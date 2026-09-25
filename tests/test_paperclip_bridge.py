"""Offline fail-closed tests for the Paperclip to Letta bridge."""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
import paperclip_bridge as bridge  # noqa: E402


def roster() -> dict:
    return {
        "workers": {
            "arthur": {"letta_id": "agent-arthur", "paperclip_agent_id": "pc-arthur", "resolved": True, "role": "Technology & Systems"},
            "cyber": {"letta_id": "agent-cyber", "paperclip_agent_id": "pc-cyber", "resolved": True, "role": "Cyber Security"},
            "edwin": {"letta_id": "agent-edwin-research", "paperclip_agent_id": "pc-edwin", "resolved": True},
        },
        "excluded": {"sabi": {"id": "agent-sabi"}, "edwin_money": {"id": "agent-edwin-money"}},
    }


def ctx(**overrides: str) -> dict[str, str]:
    base = {
        "PAPERCLIP_AGENT_ID": "pc-arthur",
        "PAPERCLIP_COMPANY_ID": "company-myhyv",
        "PAPERCLIP_API_URL": "http://127.0.0.1:3100",
        "PAPERCLIP_API_KEY": "run-token",
        "PAPERCLIP_RUN_ID": "run-1",
        "PAPERCLIP_TASK_ID": "task-1",
        "PAPERCLIP_WORKER_SLUG": "arthur",
    }
    base.update(overrides)
    return base


def issue(**overrides):
    base = {
        "id": "task-1",
        "companyId": "company-myhyv",
        "assigneeAgentId": "pc-arthur",
        "status": "todo",
        "title": "Synthetic smoke",
        "description": "Say your department only. No external action.",
        "metadata": {"taskType": "synthetic-smoke"},
    }
    base.update(overrides)
    return base


class BridgeTests(unittest.TestCase):
    def run_case(self, environment, issue_body, invoke=None, roster_body=None):
        calls = []

        def fetch(_ctx):
            return issue_body

        def fake_invoke(agent_id, prompt):
            calls.append((agent_id, prompt))
            if invoke:
                return invoke(agent_id, prompt)
            return {"text": "Arthur. Technology only.", "usage": {"total_tokens": 12}, "returncode": 0, "uncertain": False}

        with tempfile.TemporaryDirectory() as folder:
            ledger = Path(folder) / "ledger.json"
            try:
                result = bridge.execute(
                    environment,
                    roster=roster_body or roster(),
                    fetch_issue=fetch,
                    invoke_letta=fake_invoke,
                    ledger_file=ledger,
                )
                error = None
            except bridge.BridgeError as exc:
                result = None
                error = exc
            stored = json.loads(ledger.read_text()) if ledger.exists() else {"runs": []}
            return result, error, calls, stored

    def test_maps_slug_to_pinned_id_and_records_usage(self) -> None:
        result, error, calls, stored = self.run_case(ctx(), issue())
        self.assertIsNone(error)
        self.assertEqual(calls[0][0], "agent-arthur")
        self.assertEqual(result["worker"], "arthur")
        self.assertEqual(result["usage"]["total_tokens"], 12)
        self.assertFalse(result["provider_spend_cap_enforced"])
        self.assertEqual(result["provider_monetary_cost"], "unknown")
        self.assertFalse(result["paperclip_issue_marked_complete"])
        self.assertEqual(stored["runs"][0]["status"], "succeeded")
        self.assertNotIn("run-token", json.dumps(result))

    def test_rejects_wrong_assignee_before_model_call(self) -> None:
        result, error, calls, _stored = self.run_case(ctx(), issue(assigneeAgentId="pc-other"))
        self.assertIsNone(result)
        self.assertEqual(error.exit_code, 2)
        self.assertEqual(calls, [])

    def test_rejects_other_company(self) -> None:
        _result, error, calls, _stored = self.run_case(ctx(), issue(companyId="other"))
        self.assertEqual(error.exit_code, 2)
        self.assertEqual(calls, [])

    def test_missing_task_payload(self) -> None:
        _result, error, calls, _stored = self.run_case(ctx(), None)
        self.assertEqual(error.exit_code, 3)
        self.assertEqual(calls, [])

    def test_missing_task_id_env(self) -> None:
        environment = ctx()
        environment["PAPERCLIP_TASK_ID"] = ""
        _result, error, calls, _stored = self.run_case(environment, issue())
        self.assertEqual(error.exit_code, 3)
        self.assertEqual(calls, [])

    def test_duplicate_success_does_not_call_again(self) -> None:
        first, error, calls, _stored = self.run_case(ctx(), issue())
        self.assertIsNone(error)
        self.assertEqual(len(calls), 1)
        # second execution shares no ledger in run_case; simulate by calling execute twice via custom
        with tempfile.TemporaryDirectory() as folder:
            ledger = Path(folder) / "ledger.json"
            calls2 = []

            def invoke(agent_id, prompt):
                calls2.append(agent_id)
                return {"text": "ok", "usage": {"total_tokens": 1}, "returncode": 0, "uncertain": False}

            bridge.execute(ctx(), roster=roster(), fetch_issue=lambda _c: issue(), invoke_letta=invoke, ledger_file=ledger)
            with self.assertRaises(bridge.BridgeError) as raised:
                bridge.execute(ctx(PAPERCLIP_RUN_ID="run-2"), roster=roster(), fetch_issue=lambda _c: issue(), invoke_letta=invoke, ledger_file=ledger)
            self.assertEqual(raised.exception.exit_code, 4)
            self.assertEqual(len(calls2), 1)

    def test_provider_error_stops_a_second_call(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            ledger = Path(folder) / "ledger.json"
            calls = []

            def invoke(_agent, _prompt):
                calls.append(1)
                raise RuntimeError("provider down")

            with self.assertRaises(bridge.BridgeError) as first:
                bridge.execute(ctx(), roster=roster(), fetch_issue=lambda _c: issue(), invoke_letta=invoke, ledger_file=ledger)
            self.assertEqual(first.exception.exit_code, 6)
            with self.assertRaises(bridge.BridgeError) as second:
                bridge.execute(ctx(PAPERCLIP_RUN_ID="run-2"), roster=roster(), fetch_issue=lambda _c: issue(), invoke_letta=invoke, ledger_file=ledger)
            self.assertEqual(second.exception.exit_code, 5)
            self.assertEqual(len(calls), 1)

    def test_uncertain_result_is_not_success(self) -> None:
        _result, error, _calls, stored = self.run_case(
            ctx(), issue(), invoke=lambda _a, _p: {"text": "", "uncertain": True, "returncode": 0, "error": "empty"}
        )
        self.assertEqual(error.status, "uncertain")
        self.assertNotEqual(stored["runs"][0]["status"], "succeeded")

    def test_completed_issue_is_not_rerun(self) -> None:
        _result, error, calls, _stored = self.run_case(ctx(), issue(status="done"))
        self.assertEqual(error.exit_code, 4)
        self.assertEqual(calls, [])

    def test_unresolved_and_excluded_ids_fail_closed(self) -> None:
        unresolved = roster()
        unresolved["workers"]["arthur"]["resolved"] = False
        _result, error, calls, _stored = self.run_case(ctx(), issue(), roster_body=unresolved)
        self.assertEqual(error.exit_code, 7)
        self.assertEqual(calls, [])
        _result, error, calls, _stored = self.run_case(ctx(PAPERCLIP_WORKER_SLUG="sabi"), issue(), roster_body=roster())
        self.assertEqual(error.exit_code, 2)
        self.assertEqual(calls, [])
        _result, error, calls, _stored = self.run_case(ctx(PAPERCLIP_WORKER_SLUG="edwin_money"), issue(), roster_body=roster())
        self.assertEqual(error.exit_code, 2)

    def test_disallowed_task_type_and_cyber_readonly_type(self) -> None:
        _result, error, calls, _stored = self.run_case(ctx(), issue(metadata={"taskType": "send-payment"}))
        self.assertEqual(error.exit_code, 2)
        self.assertEqual(calls, [])
        cyber_issue = issue(
            assigneeAgentId="pc-cyber",
            metadata={"taskType": "security-review-readonly"},
        )
        result, error, calls, _stored = self.run_case(
            ctx(PAPERCLIP_AGENT_ID="pc-cyber", PAPERCLIP_WORKER_SLUG="cyber", PAPERCLIP_TASK_ID="task-1"),
            cyber_issue,
        )
        self.assertIsNone(error)
        self.assertEqual(calls[0][0], "agent-cyber")
        self.assertIn("Do not change settings", calls[0][1])

    def test_checked_in_roster_is_unresolved_and_excludes_both_edwins_from_substitution(self) -> None:
        live = json.loads((ROOT / "config" / "paperclip-roster.json").read_text())
        self.assertNotIn("sabi", live["workers"])
        self.assertIn("sabi", live["excluded"])
        self.assertFalse(live["paperclip_company_imported"])
        for slug in ("arthur", "mrg", "edwin", "agnes", "cyber"):
            self.assertFalse(live["workers"][slug]["resolved"])
        self.assertNotEqual(live["workers"]["edwin"]["letta_id"], live["excluded"]["edwin_money"]["id"])
        self.assertIsNone(live["workers"]["cyber"]["letta_id"])


if __name__ == "__main__":
    unittest.main()
