#!/usr/bin/env python3
"""Run one bounded, receipt-backed Mini-HYV council request.

This remains custom routing through the parent process. It is intentionally
separate from the LifeOS website and never changes any website code.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from ask import ask
from council import Limits, ReceiptCouncil

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--task", required=True, help="One bounded owner request.")
    parser.add_argument(
        "--departments",
        default="arthur,mrg",
        help="Comma-separated department keys. Sabi is synthesis only.",
    )
    parser.add_argument("--max-calls", type=int, default=3)
    parser.add_argument("--max-tokens", type=int, default=90000)
    parser.add_argument("--request-id", default=None)
    args = parser.parse_args()

    config = json.loads((ROOT / "config" / "agents.json").read_text())
    council = ReceiptCouncil(
        ask_fn=ask,
        agents=config["agents"],
        evidence_dir=ROOT / "evidence" / "council-v2",
        limits=Limits(
            max_calls=args.max_calls,
            max_total_reported_tokens=args.max_tokens,
        ),
    )
    departments = tuple(x.strip() for x in args.departments.split(",") if x.strip())
    decision = council.request(
        principal="Michael",
        task=args.task,
        departments=departments,
        request_id=args.request_id,
    )
    print("ROUTING: custom receipt-backed routing; not native Letta A2A")
    print("RECEIPTS:", ", ".join(decision.cited_receipt_ids))
    print("TOKENS:", decision.total_reported_tokens)
    print()
    print(decision.answer)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
