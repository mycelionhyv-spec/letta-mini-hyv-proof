"""Offline checks for the five-agent Mini-HYV config."""

from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AGENTS_PATH = ROOT / "config" / "agents.json"

ORIGINAL = {
    "sabi": "agent-local-df17783d-ebc0-4fb7-8d8e-7b11f603fb81",
    "arthur": "agent-local-453f42d0-f174-4046-892e-0ce2b5c2ae2e",
    "mrg": "agent-local-bc3abe43-c523-41d1-b433-261ea1697306",
}
ADDED = {
    "edwin": "agent-local-738aaad8-bf19-4151-bd2c-999770104147",
    "agnes": "agent-local-29dd7050-8717-4f99-b0ae-0f6b657fb104",
}


class AgentsConfigTests(unittest.TestCase):
    def setUp(self) -> None:
        self.cfg = json.loads(AGENTS_PATH.read_text())
        self.agents = self.cfg["agents"]

    def test_exactly_five_agents(self) -> None:
        self.assertEqual(set(self.agents), {"sabi", "arthur", "mrg", "edwin", "agnes"})

    def test_original_three_ids_unchanged(self) -> None:
        for key, aid in ORIGINAL.items():
            self.assertEqual(self.agents[key]["id"], aid)

    def test_new_agents_have_distinct_ids(self) -> None:
        ids = [self.agents[k]["id"] for k in ("sabi", "arthur", "mrg", "edwin", "agnes")]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertEqual(self.agents["edwin"]["id"], ADDED["edwin"])
        self.assertEqual(self.agents["agnes"]["id"], ADDED["agnes"])

    def test_persona_files_exist(self) -> None:
        self.assertTrue((ROOT / "config" / "personas" / "edwin.md").is_file())
        self.assertTrue((ROOT / "config" / "personas" / "agnes.md").is_file())


class FiveAgentEvidenceTests(unittest.TestCase):
    def test_required_json_parses_and_has_output(self) -> None:
        folder = ROOT / "evidence" / "five-agent"
        required = [
            "00-report.json",
            "01-identity-edwin.json",
            "01-identity-agnes.json",
            "02-team-sabi.json",
            "03-memory-read-edwin.json",
            "03-memory-read-agnes.json",
            "04-isolation-agnes_asked_glasswell.json",
            "05-conflict-agnes.json",
            "05-conflict-sabi.json",
        ]
        for name in required:
            path = folder / name
            self.assertTrue(path.is_file(), name)
            data = json.loads(path.read_text())
            self.assertTrue(isinstance(data, dict), name)
            if name == "00-report.json":
                self.assertIn("tests", data)
                continue
            parsed = data.get("parsed") or {}
            result = parsed.get("result") if isinstance(parsed, dict) else None
            self.assertTrue(isinstance(result, str) and len(result) > 8, name)


if __name__ == "__main__":
    unittest.main()
