# Council V2 — Controlled Routing

This is the next step after the Mini-HYV proof. It is a **custom, receipt-backed router**, not native Letta A2A and not a website integration.

## What V2 changes

| V1 weakness | V2 control |
|---|---|
| Sabi could speak as departments | Final answer must cite every exact departmental receipt or the run fails. |
| Routing was ad hoc | Every job has a principal, target department, task hash and receipt id. |
| Outputs could be altered silently | Input and output SHA-256 hashes are stored with every receipt. |
| Costs could drift | Max calls and reported-token budgets stop the run. |
| “Agent chat” could be overstated | Every artifact labels the path as custom routing, not Letta native A2A. |

## What it does not claim

- It does **not** prove native Letta Groups or REST agent-to-agent messaging.
- It does **not** authenticate a website owner.
- It does **not** connect to the LifeOS frontend, Gemini or Google Sheets.
- It does **not** make model output true; it makes the source, route and limits auditable.

## Offline checks

Run these before any live model call:

```bash
.venv/bin/python -m unittest tests/test_council.py
```

The tests prove:

1. two departments produce two receipts;
2. Sabi must cite both receipts;
3. missing citations fail closed;
4. the call budget stops a third call when only two are allowed;
5. unknown departments fail before a model call.

## One bounded live run

```bash
.venv/bin/python src/run_council_v2.py \
  --task "Should LifeOS V1 add a private daily reflection feature? Give a technical and creative recommendation with scope, risks and one next step." \
  --departments arthur,mrg \
  --max-calls 3 \
  --max-tokens 90000 \
  --request-id reflection-v1
```

It writes a JSON evidence record under `evidence/council-v2/`. The record contains the exact receipt ids, hashes, outputs, cited ids and reported-token total.

## Promotion gate

V2 is ready to inform a website build only when all of the following are true:

- offline tests pass;
- three different live requests complete within the declared budget;
- every final answer cites every departmental receipt;
- no agent claims native collaboration;
- Michael can read the evidence record and trace each claim back to its source.

After that, the next build is a separate owner-authenticated Sabi surface. It must not reuse the old deleted panel or silently wire council output into LifeOS.
