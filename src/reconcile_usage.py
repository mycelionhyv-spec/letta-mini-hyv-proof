"""Reconcile the immutable five-agent call transcripts without pricing guesses."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "evidence" / "five-agent"
OUTPUT = EVIDENCE / "token-reconciliation.json"
FIELDS = ("prompt_tokens", "completion_tokens", "cached_input_tokens", "total_tokens",
          "context_tokens", "cache_write_tokens", "reasoning_tokens")


def reconcile(folder: Path = EVIDENCE) -> dict:
    rows = []
    for path in sorted(folder.glob("*.json")):
        if path.name in {"00-report.json", OUTPUT.name}:
            continue
        raw = json.loads(path.read_text())
        usage = (raw.get("parsed") or {}).get("usage")
        if raw.get("returncode") != 0 or not isinstance(usage, dict):
            raise ValueError(f"{path.name}: failed call or missing usage")
        for field in FIELDS:
            if type(usage.get(field)) is not int or usage[field] < 0:
                raise ValueError(f"{path.name}: invalid {field}")
        accounted = (usage["prompt_tokens"] + usage["completion_tokens"]
                     + usage["cached_input_tokens"])
        if usage["total_tokens"] != accounted:
            raise ValueError(f"{path.name}: total_tokens != prompt + completion + cached_input")
        rows.append({"file": path.name, "agent_id": raw.get("agent_id"),
                     **{field: usage[field] for field in FIELDS}})
    if len(rows) != 28:
        raise ValueError(f"Expected the 28 archived headless calls, found {len(rows)}")
    totals = {field: sum(row[field] for row in rows) for field in FIELDS}
    return {
        "source": "28 archived Letta Code JSON transcripts from 2026-09-22",
        "formula": "total_tokens = prompt_tokens + completion_tokens + cached_input_tokens",
        "rows": rows, "totals": totals,
        "interpretation": (
            "cached_input_tokens explains the difference between the listed prompt-plus-completion "
            "and total fields in every record. context_tokens is a separate raw field, not an "
            "additional charge. The transcripts do not establish the xAI invoice, cache pricing, "
            "or the provider-billable amount; actual monetary cost remains unknown."
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Verify the committed report without rewriting it")
    args = parser.parse_args()
    result = reconcile()
    if args.check:
        if not OUTPUT.exists() or json.loads(OUTPUT.read_text()) != result:
            raise SystemExit("Committed token report is missing or stale")
    else:
        OUTPUT.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result["totals"], sort_keys=True))


if __name__ == "__main__":
    main()
