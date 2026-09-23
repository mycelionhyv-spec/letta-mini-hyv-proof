#!/usr/bin/env python3
"""Targeted live check on the original Letta machine; no credentials in evidence."""

from __future__ import annotations

import argparse
import json
import secrets
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from ask import ask, text_of  # noqa: E402
from blind_isolation import (CROSS_CHECKS, OWNERS, assess_cross_reply,
                             assess_own_reply, blind_question, own_question,
                             teach_prompt)  # noqa: E402

AGENTS = json.loads((ROOT / "config" / "agents.json").read_text())["agents"]


def record(output: Path, stage: str, name: str, agent: str, prompt: str) -> tuple[dict, str]:
    raw = ask(AGENTS[agent]["id"], prompt, new_conversation=True)
    response = text_of(raw)
    evidence = {"stage": stage, "subject": name, "agent_id": AGENTS[agent]["id"],
                "prompt": prompt, "response": response, "raw": raw}
    (output / f"{stage}-{name}.json").write_text(json.dumps(evidence, indent=2) + "\n")
    return raw, response


def success(raw: dict) -> bool:
    parsed = raw.get("parsed")
    return (raw.get("returncode") == 0 and isinstance(parsed, dict)
            and parsed.get("subtype") == "success" and not parsed.get("is_error"))


def run(output: Path) -> dict:
    output.mkdir(parents=True, exist_ok=False)
    # New markers prevent earlier contaminated prompts from satisfying a blind check.
    markers = {owner: "AUDIT-" + secrets.token_urlsafe(18) for owner in OWNERS}
    report = {"started_at": datetime.now(timezone.utc).isoformat(),
              "routing": "direct local Letta Code calls; no native A2A",
              "model_behavior_status": "INCOMPLETE", "storage_isolation_status": "UNVERIFIED",
              "warning": "Model answers alone cannot establish a private MemFS boundary.",
              "markers": markers, "checks": []}

    def save_report() -> None:
        (output / "result.json").write_text(json.dumps(report, indent=2) + "\n")

    try:
        for owner, marker in markers.items():
            raw, response = record(output, "teach", owner, owner, teach_prompt(marker))
            report["checks"].append({"kind": "teach", "owner": owner,
                                     "agent_id": AGENTS[owner]["id"], "call_succeeded": success(raw),
                                     "response": response})
        for owner, marker in markers.items():
            raw, response = record(output, "own", owner, owner, own_question())
            report["checks"].append({"kind": "own_recall", "owner": owner,
                                     "agent_id": AGENTS[owner]["id"],
                                     "pass": assess_own_reply(response, marker, success(raw)),
                                     "response": response})
        for questioned, owner in CROSS_CHECKS:
            prompt = blind_question(owner)
            if any(value in prompt for value in markers.values()):
                raise ValueError("Blind question accidentally exposes a test marker")
            raw, response = record(output, "cross", f"{questioned}-asks-{owner}", questioned, prompt)
            report["checks"].append({"kind": "blind_cross", "questioned": questioned,
                                     "owner": owner, "agent_id": AGENTS[questioned]["id"],
                                     "pass": assess_cross_reply(response, markers[owner], success(raw)),
                                     "response": response})
        report["model_behavior_status"] = (
            "PASS" if all(c.get("pass", c.get("call_succeeded", False)) for c in report["checks"])
            else "FAIL"
        )
    except Exception as exc:
        report["model_behavior_status"] = "INCOMPLETE"
        report["interrupted_by"] = f"{type(exc).__name__}: {exc}"
        raise
    finally:
        report["finished_at"] = datetime.now(timezone.utc).isoformat()
        save_report()
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, help="Fresh evidence directory; must not exist")
    args = parser.parse_args()
    suffix = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    destination = args.output or ROOT / "evidence" / "five-agent" / "blind-isolation" / suffix
    result = run(destination)
    print(json.dumps({"evidence": str(destination), "model_behavior_status":
                      result["model_behavior_status"], "storage_isolation_status":
                      result["storage_isolation_status"]}))


if __name__ == "__main__":
    main()
