"""Concrete offline regression checks: auth, concurrency, receipts and authority."""
import http.client
import json
import multiprocessing
import os
import tempfile
import threading
import unittest
from http.server import ThreadingHTTPServer
from pathlib import Path
from subprocess import CompletedProcess
from unittest.mock import Mock, patch

from test_paperclip_bridge import bridge, ctx, issue, roster


def hold_lock(path, ready, release):
    with bridge.invocation_lock(path):
        ready.set()
        release.wait(5)


class BridgeGuards(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.ledger = Path(self.tmp.name) / "private" / "ledger.json"
        self.invoke = Mock(return_value={"text": "Arthur: Technology & Systems", "returncode": 0})
        self.fetch = Mock(return_value=issue())

    def execute(self, **kwargs):
        return bridge.execute(kwargs.get("env", ctx()), roster=kwargs.get("roster", roster()),
                              fetch_issue=self.fetch, invoke_letta=self.invoke, ledger_file=self.ledger)

    def test_cross_process_lock_blocks_then_releases(self):
        context = multiprocessing.get_context("spawn")
        ready, release = context.Event(), context.Event()
        process = context.Process(target=hold_lock, args=(self.ledger, ready, release))
        process.start()
        try:
            self.assertTrue(ready.wait(5))
            with self.assertRaises(bridge.BridgeError) as error:
                self.execute()
            self.assertEqual(error.exception.exit_code, 8)
            self.invoke.assert_not_called()
            self.fetch.assert_not_called()
        finally:
            release.set()
            process.join(5)
            if process.is_alive():
                process.terminate()
                process.join()
        self.assertEqual(process.exitcode, 0)
        self.execute()
        self.invoke.assert_called_once()

    def test_receipt_is_durable_private_and_identifies_result(self):
        result = self.execute()
        receipt = Path(result["receipt_path"])
        self.assertEqual(json.loads(receipt.read_text()), result)
        for key, expected in (("company_id", "company-myhyv"), ("task_id", "task-1"),
                              ("run_id", "run-1"), ("letta_id", "agent-arthur"),
                              ("paperclip_agent_id", "pc-arthur")):
            self.assertEqual(result[key], expected)
        self.assertEqual(result["output_sha256"], bridge.sha256_text(result["text"]))
        self.assertEqual(receipt.stat().st_mode & 0o777, 0o600)
        self.assertEqual(receipt.parent.stat().st_mode & 0o777, 0o700)
        self.assertEqual(self.ledger.stat().st_mode & 0o777, 0o600)
        self.assertNotIn("run-token", receipt.read_text() + self.ledger.read_text())

    def test_receipt_failure_does_not_allow_second_call(self):
        original = bridge.write_ledger
        def fail_receipt(path, data):
            if path.parent.name == "receipts":
                raise OSError("disk full")
            original(path, data)
        with patch.object(bridge, "write_ledger", side_effect=fail_receipt):
            with self.assertRaises(OSError):
                self.execute()
        self.assertEqual(json.loads(self.ledger.read_text())["runs"][0]["status"], "started")
        with self.assertRaises(bridge.BridgeError) as error:
            self.execute()
        self.assertEqual(error.exception.exit_code, 5)
        self.invoke.assert_called_once()

    def test_excluded_duplicate_and_wrong_worker_fail_before_lookup(self):
        for scenario in ("excluded", "duplicate", "wrong_worker"):
            with self.subTest(scenario=scenario):
                mapping = roster()
                env = ctx()
                if scenario == "excluded":
                    mapping["workers"]["arthur"]["letta_id"] = "agent-edwin-money"
                elif scenario == "duplicate":
                    mapping["workers"]["cyber"]["letta_id"] = "agent-arthur"
                else:
                    env["PAPERCLIP_AGENT_ID"] = "pc-cyber"
                with self.assertRaises(bridge.BridgeError):
                    self.execute(env=env, roster=mapping)
        self.fetch.assert_not_called()
        self.invoke.assert_not_called()

    def test_blocked_or_missing_task_state_never_calls_model(self):
        for state in (None, "blocked", "backlog", "in_review"):
            self.fetch.return_value = issue(status=state)
            with self.assertRaises(bridge.BridgeError):
                self.execute()
        self.invoke.assert_not_called()

    def test_letta_has_no_tools_or_bridge_credentials(self):
        response = CompletedProcess([], 0, json.dumps({"subtype": "success", "result": "ok"}), "secret-stderr")
        with patch.dict(os.environ, {"MYHYV_BRIDGE_WEBHOOK_TOKEN": "bridge-secret",
                                     "PAPERCLIP_API_KEY": "paperclip-secret", "BRIDGE_TOKEN": "bridge-secret",
                                     "XAI_API_KEY": "provider-test-only", "LETTA_LOCAL_BACKEND_DIR": "/test/store"}), \
             patch("subprocess.run", return_value=response) as run:
            result = bridge.default_invoke_letta("agent-arthur", "bounded")
        args, kwargs = run.call_args
        command = args[0]
        self.assertEqual(command[command.index("--tools") + 1], "")
        self.assertIn("--no-skills", command)
        self.assertIn("--no-mods", command)
        child = kwargs["env"]
        self.assertFalse(any(key.startswith(("PAPERCLIP_", "MYHYV_")) for key in child))
        self.assertNotIn("BRIDGE_TOKEN", child)
        self.assertEqual(child["XAI_API_KEY"], "provider-test-only")
        self.assertEqual(child["LETTA_LOCAL_BACKEND_DIR"], "/test/store")
        self.assertNotIn("secret-stderr", json.dumps(result))

    def test_provider_error_detail_is_not_persisted_or_returned(self):
        self.invoke.side_effect = RuntimeError("Bearer private-secret")
        with self.assertRaises(bridge.BridgeError) as error:
            self.execute()
        self.assertNotIn("private-secret", str(error.exception) + self.ledger.read_text())


class HttpGuards(unittest.TestCase):
    def test_auth_precedes_body_read_and_lookup(self):
        with tempfile.TemporaryDirectory() as folder:
            fetch, invoke = Mock(), Mock()
            handler = bridge.make_handler(roster(), {"MYHYV_BRIDGE_WEBHOOK_TOKEN": "test-token"},
                                          fetch, invoke, Path(folder) / "ledger.json")
            server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            try:
                # Declared bodies are deliberately not sent. Auth must reject without waiting.
                for headers, length, expected in (([], "123", 401),
                        (["wrong"], "123", 401), (["test-token", "test-token"], "123", 401),
                        (["test-token"], str(bridge.MAX_WAKE_BYTES + 1), 413)):
                    connection = http.client.HTTPConnection("127.0.0.1", server.server_port, timeout=2)
                    try:
                        connection.putrequest("POST", "/wake/arthur")
                        connection.putheader("Content-Length", length)
                        for value in headers:
                            connection.putheader("X-MyHYv-Bridge-Token", value)
                        connection.endheaders()
                        response = connection.getresponse()
                        self.assertEqual(response.status, expected)
                        response.read()
                    finally:
                        connection.close()
                connection = http.client.HTTPConnection("127.0.0.1", server.server_port, timeout=2)
                try:
                    connection.request("POST", "/wake/arthur", "bad-json", {"X-MyHYv-Bridge-Token": "test-token"})
                    response = connection.getresponse()
                    self.assertEqual(response.status, 400)
                    response.read()
                finally:
                    connection.close()
                fetch.assert_not_called()
                invoke.assert_not_called()
                self.assertFalse((Path(folder) / "ledger.json").exists())
            finally:
                server.shutdown()
                server.server_close()
                thread.join(2)
