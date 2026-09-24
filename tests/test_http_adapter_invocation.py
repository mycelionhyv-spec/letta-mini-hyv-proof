"""Invoke the bridge the way Paperclip's HTTP adapter actually does."""

from __future__ import annotations

import json
import os
import socket
import subprocess
import sys
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INVOKE = ROOT / "tests" / "paperclip_http_adapter_invoke.mjs"


class FakePaperclip(BaseHTTPRequestHandler):
    issues = {}
    fetched = []

    def log_message(self, fmt, *args):
        return

    def do_GET(self):
        FakePaperclip.fetched.append(self.path)
        issue = FakePaperclip.issues.get(self.path)
        if issue is None:
            self.send_response(404)
            self.end_headers()
            return
        data = json.dumps(issue).encode()
        self.send_response(200)
        self.send_header("content-type", "application/json")
        self.send_header("content-length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


def free_port() -> int:
    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    sock.close()
    return port


class HttpAdapterInvocationTest(unittest.TestCase):
    def test_process_adapter_excerpt_has_no_task_id_and_http_posts_context(self) -> None:
        process = (ROOT / "paperclip/upstream/process-adapter-does-not-set-task-id.txt").read_text()
        http = (ROOT / "paperclip/upstream/http-adapter-posts-context.txt").read_text()
        self.assertNotIn("PAPERCLIP_TASK_ID", process)
        self.assertIn("context", http)
        invoke = INVOKE.read_text()
        self.assertIn("agentId: agent.id", invoke)
        self.assertIn("context,", invoke)
        self.assertNotIn("issues?assignee", invoke)

    def test_adapter_post_reaches_only_the_named_task(self) -> None:
        folder = Path(self.id().replace(".", "_"))
        # isolate files under tmp via TemporaryDirectory semantics manually
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            roster = {
                "workers": {
                    "arthur": {
                        "letta_id": "agent-arthur",
                        "resolved": True,
                        "paperclip_agent_id": "pc-arthur",
                    }
                },
                "excluded": {"sabi": {"id": "agent-sabi"}},
            }
            roster_path = tmp_path / "roster.json"
            roster_path.write_text(json.dumps(roster))
            ledger = tmp_path / "ledger.json"
            calls = tmp_path / "letta-calls.json"
            letta = tmp_path / "letta.sh"
            letta.write_text(
                "#!/bin/sh\n"
                "printf '%s\\n' \"$*\" >> \"$CALLS\"\n"
                "printf '%s\\n' '{\"subtype\":\"success\",\"is_error\":false,\"result\":\"Arthur. Technology only.\",\"usage\":{\"total_tokens\":4}}'\n"
            )
            letta.chmod(0o755)

            FakePaperclip.fetched = []
            FakePaperclip.issues = {
                "/api/issues/task-arthur": {
                    "id": "task-arthur",
                    "companyId": "company-myhyv",
                    "assigneeAgentId": "pc-arthur",
                    "status": "todo",
                    "title": "Arthur synthetic",
                    "description": "Say your department only.",
                    "metadata": {"taskType": "synthetic-smoke"},
                },
                "/api/issues/task-other": {
                    "id": "task-other",
                    "companyId": "company-myhyv",
                    "assigneeAgentId": "pc-arthur",
                    "status": "todo",
                    "title": "Do not fetch this",
                    "description": "Wrong task.",
                    "metadata": {"taskType": "synthetic-smoke"},
                },
            }
            api = ThreadingHTTPServer(("127.0.0.1", 0), FakePaperclip)
            api_port = api.server_address[1]
            threading.Thread(target=api.serve_forever, daemon=True).start()

            env = os.environ.copy()
            env.update({
                "MYHYV_BRIDGE_PORT": "0",
                "MYHYV_BRIDGE_LEDGER": str(ledger),
                "MYHYV_PAPERCLIP_COMPANY_ID": "company-myhyv",
                "PAPERCLIP_API_URL": f"http://127.0.0.1:{api_port}",
                "PAPERCLIP_API_KEY": "run-token",
                "LETTA_BIN": str(letta),
                "CALLS": str(calls),
                "CI": "1",
                "NO_COLOR": "1",
            })
            # The server loads the roster from the repo path. Point it at the temp roster
            # by swapping is not supported, so write over is unsafe. Use a copy of the
            # module path via PYTHONPATH and a wrapper. Instead, run serve from a copied tree.
            bridge_src = (ROOT / "src" / "paperclip_bridge.py").read_text()
            bridge_src = bridge_src.replace(
                'ROSTER_PATH = ROOT / "config" / "paperclip-roster.json"',
                f'ROSTER_PATH = Path(r"{roster_path}")',
            )
            bridge_path = tmp_path / "paperclip_bridge.py"
            bridge_path.write_text(bridge_src)
            proc = subprocess.Popen(
                [sys.executable, str(bridge_path), "--serve"],
                env=env,
                stderr=subprocess.PIPE,
                stdout=subprocess.PIPE,
                text=True,
            )
            try:
                line = proc.stderr.readline()
                self.assertTrue(line.startswith("listening 127.0.0.1 "), line)
                port = int(line.split()[-1])
                base = {
                    "BRIDGE_URL": f"http://127.0.0.1:{port}/wake/arthur",
                    "AGENT_ID": "pc-arthur",
                    "RUN_ID": "run-1",
                    "WAKE_CONTEXT": json.dumps({
                        "issueId": "task-arthur",
                        "taskId": "task-arthur",
                        "wakeReason": "issue_assigned",
                        "otherVisibleIssueId": "task-other",
                    }),
                }
                good = subprocess.run(
                    ["node", str(INVOKE)],
                    env={**env, **base},
                    capture_output=True,
                    text=True,
                    check=False,
                )
                self.assertEqual(good.returncode, 0, good.stdout + good.stderr)
                payload = json.loads(json.loads(good.stdout)["body"])
                self.assertEqual(payload["task_id"], "task-arthur")
                self.assertEqual(payload["letta_id"], "agent-arthur")
                self.assertTrue(payload["text"].startswith("Arthur."))
                issue_fetches = [path for path in FakePaperclip.fetched if path.startswith("/api/issues/")]
                self.assertEqual(issue_fetches, ["/api/issues/task-arthur"])

                missing = subprocess.run(
                    ["node", str(INVOKE)],
                    env={**env, **base, "WAKE_CONTEXT": json.dumps({"wakeReason": "issue_assigned"})},
                    capture_output=True,
                    text=True,
                    check=False,
                )
                self.assertNotEqual(missing.returncode, 0)
                self.assertEqual(
                    [path for path in FakePaperclip.fetched if path.startswith("/api/issues/")],
                    ["/api/issues/task-arthur"],
                )
                self.assertNotIn("task-other", "".join(FakePaperclip.fetched))

                mismatch = subprocess.run(
                    ["node", str(INVOKE)],
                    env={**env, **base, "AGENT_ID": "pc-other", "RUN_ID": "run-3",
                         "WAKE_CONTEXT": json.dumps({"issueId": "task-arthur"})},
                    capture_output=True,
                    text=True,
                    check=False,
                )
                self.assertNotEqual(mismatch.returncode, 0)
                self.assertEqual(
                    [path for path in FakePaperclip.fetched if path.startswith("/api/issues/")],
                    ["/api/issues/task-arthur"],
                )
                self.assertEqual(calls.read_text().count("agent-arthur"), 1)
            finally:
                proc.terminate()
                proc.wait(timeout=5)
                api.shutdown()


if __name__ == "__main__":
    unittest.main()
