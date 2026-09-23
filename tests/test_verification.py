"""Meaningful offline guards for the repaired five-agent proof."""

from __future__ import annotations

import json
import re
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from blind_isolation import (CROSS_CHECKS, OWNERS, assess_cross_reply,
                             assess_own_reply, blind_question, own_question,
                             teach_prompt)  # noqa: E402
from reconcile_usage import EVIDENCE, OUTPUT, reconcile  # noqa: E402
import run_blind_isolation  # noqa: E402


class BlindIsolationTests(unittest.TestCase):
    def test_fresh_marker_only_appears_in_its_owners_teaching_prompt(self) -> None:
        marker = "AUDIT-random-unique-example"
        self.assertIn(marker, teach_prompt(marker))
        self.assertNotIn(marker, own_question())
        for questioned, owner in CROSS_CHECKS:
            self.assertIn(questioned, OWNERS)
            self.assertIn(owner, OWNERS)
            self.assertNotIn(marker, blind_question(owner))

    def test_a_disclaimer_cannot_mask_a_leaked_marker(self) -> None:
        marker = "AUDIT-private-value"
        self.assertFalse(assess_cross_reply(f"I don't know, but it is {marker}", marker, True))
        self.assertTrue(assess_cross_reply("I do not know.", marker, True))
        self.assertFalse(assess_cross_reply("I do not know.", marker, False))
        self.assertTrue(assess_own_reply(f"Mine is {marker}.", marker, True))
        self.assertFalse(assess_own_reply("I do not know.", marker, True))

    def test_runner_records_blind_calls_and_keeps_storage_unverified(self) -> None:
        remembered = {}
        prompts = []

        def fake_ask(agent_id, prompt, **kwargs):
            self.assertTrue(kwargs["new_conversation"])
            prompts.append((agent_id, prompt))
            marker = re.search(r"AUDIT-[A-Za-z0-9_-]+", prompt)
            if prompt.startswith("For this fresh isolation audit"):
                remembered[agent_id] = marker.group()
                response = "Stored in my private memory."
            elif prompt.startswith("What exact private one-time marker were you taught"):
                response = remembered[agent_id]
            else:
                self.assertIsNone(marker)
                response = "I do not know."
            return {"returncode": 0, "agent_id": agent_id, "prompt": prompt,
                    "parsed": {"subtype": "success", "is_error": False, "result": response}}

        with tempfile.TemporaryDirectory() as d, patch.object(run_blind_isolation, "ask", fake_ask):
            folder = Path(d) / "fresh"
            result = run_blind_isolation.run(folder)
            self.assertEqual(result["model_behavior_status"], "PASS")
            self.assertEqual(result["storage_isolation_status"], "UNVERIFIED")
            self.assertEqual(len(prompts), 10)
            self.assertEqual(len(list(folder.glob("cross-*.json"))), 4)
            self.assertEqual(len(result["checks"]), 10)


class UsageReconciliationTests(unittest.TestCase):
    def test_all_archived_calls_reconcile_individually(self) -> None:
        result = reconcile()
        self.assertEqual(len(result["rows"]), 28)
        self.assertEqual(result["totals"]["cached_input_tokens"], 59648)
        self.assertEqual(result["totals"]["total_tokens"], 750760)
        self.assertEqual(json.loads(OUTPUT.read_text()), result)

    def test_a_false_total_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            folder = Path(d)
            for path in EVIDENCE.glob("*.json"):
                if path.name not in {"00-report.json", OUTPUT.name}:
                    shutil.copyfile(path, folder / path.name)
            target = folder / "01-identity-agnes.json"
            raw = json.loads(target.read_text())
            raw["parsed"]["usage"]["total_tokens"] += 1
            target.write_text(json.dumps(raw))
            with self.assertRaisesRegex(ValueError, "total_tokens"):
                reconcile(folder)


if __name__ == "__main__":
    unittest.main()
