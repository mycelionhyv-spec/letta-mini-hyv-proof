"""Offline contract tests for the receipt-backed council."""

from __future__ import annotations

import re
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from council import BudgetExceeded, CouncilError, Limits, ReceiptCouncil  # noqa: E402


AGENTS = {
    "sabi": {"id": "sabi-id", "name": "Sabi"},
    "arthur": {"id": "arthur-id", "name": "Arthur"},
    "mrg": {"id": "mrg-id", "name": "Mr G"},
}


def result(text: str, tokens: int = 10) -> dict:
    return {
        "returncode": 0,
        "elapsed_s": 0.01,
        "parsed": {
            "result": text,
            "usage": {
                "prompt_tokens": tokens - 2,
                "completion_tokens": 2,
                "total_tokens": tokens,
            },
        },
    }


class ReceiptCouncilTests(unittest.TestCase):
    def make_council(self, ask_fn, **limit_overrides):
        limits = Limits(**limit_overrides)
        return ReceiptCouncil(
            ask_fn=ask_fn,
            agents=AGENTS,
            evidence_dir=Path(tempfile.mkdtemp()),
            limits=limits,
        )

    def test_decision_must_cite_every_receipt(self):
        def ask(agent_id, prompt, **_):
            if agent_id == "arthur-id":
                return result("Feasible with a bounded adapter.")
            if agent_id == "mrg-id":
                return result("Make it feel quiet and human.")
            ids = re.findall(r"\[receipt:(rcpt-[A-Za-z0-9]+)\]", prompt)
            return result(
                "Decision: prototype the bounded adapter. "
                + " ".join(f"[receipt:{rid}]" for rid in ids)
            )

        council = self.make_council(ask)
        decision = council.request(
            principal="Michael",
            task="Choose a bounded LifeOS differentiator.",
            departments=("arthur", "mrg"),
            request_id="test-pass",
        )
        self.assertEqual(len(decision.receipts), 2)
        self.assertEqual(set(decision.cited_receipt_ids), {r.id for r in decision.receipts})
        self.assertEqual(decision.total_reported_tokens, 30)

    def test_uncited_department_claim_fails_closed(self):
        def ask(agent_id, prompt, **_):
            if agent_id == "arthur-id":
                return result("Technical answer.")
            if agent_id == "mrg-id":
                return result("Creative answer.")
            ids = re.findall(r"\[receipt:(rcpt-[A-Za-z0-9]+)\]", prompt)
            return result("Only one receipt is enough [receipt:" + ids[0] + "]")

        council = self.make_council(ask)
        with self.assertRaisesRegex(CouncilError, "receipt invariant"):
            council.request(
                principal="Michael",
                task="Test receipt enforcement.",
                departments=("arthur", "mrg"),
                request_id="test-fail-closed",
            )

    def test_budget_stops_extra_calls(self):
        def ask(agent_id, prompt, **_):
            return result("A reply [receipt:rcpt-placeholder]")

        council = self.make_council(ask, max_calls=2)
        with self.assertRaises(BudgetExceeded):
            council.request(
                principal="Michael",
                task="This needs three calls including synthesis.",
                departments=("arthur", "mrg"),
            )

    def test_unknown_department_is_rejected_before_model_call(self):
        called = False

        def ask(agent_id, prompt, **_):
            nonlocal called
            called = True
            return result("Should not run.")

        council = self.make_council(ask)
        with self.assertRaisesRegex(CouncilError, "Unknown department"):
            council.request(
                principal="Michael",
                task="Route to a made-up agent.",
                departments=("winston",),
            )
        self.assertFalse(called)


if __name__ == "__main__":
    unittest.main()
