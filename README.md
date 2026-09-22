# MYHYV — Letta Mini-HYV working proof

Disposable test: can Letta hold **identity, memory, delegation and disagreement** for three MyHYv agents?

This is **not** a website change. The LifeOS frontend was inspected read-only and was not edited.

## What actually ran

| Layer | What we used | Cost |
|---|---|---|
| Agent runtime | **Letta Code 0.32.15**, `--backend local`, SQLite/MemFS on this machine | $0, no Letta account |
| Cloud free tier | **Not used.** Needs `LETTA_API_KEY`. Free Cloud is 3 managed agents + rotating models | n/a |
| Native REST Groups / `send_message_to_agent_*` | **Not available** on Letta Code local. Those APIs belong to Letta Server / Cloud | n/a |
| Models | **xAI Grok 4.3** (`xai/grok-4.3`, reasoning `none`) via the sandbox `XAI_API_KEY` | BYOK, not Letta credits |
| Embeddings | Not used. Local MemFS does not require OpenAI embeddings | $0 |

Letta the product is free locally. Model tokens are not.

## Agents (exactly three)

| Name | Role | Local id |
|---|---|---|
| Sabi | Coordinator. Michael's only interface | `agent-local-df17783d-ebc0-4fb7-8d8e-7b11f603fb81` |
| Arthur | Technology & Systems | `agent-local-453f42d0-f174-4046-892e-0ce2b5c2ae2e` |
| Mr G | Creative & Experience | `agent-local-bc3abe43-c523-41d1-b433-261ea1697306` |

IDs live in `config/agents.json`. Recreate with `letta --backend local agents create` if you clone cold.

## Launch (this machine)

```bash
cd letta-proof
uv venv .venv
uv pip install --python .venv/bin/python letta-client letta
# connect a model (once)
.venv/bin/letta backend local
.venv/bin/letta --backend local connect openai-compatible --base-url https://api.x.ai/v1 --api-key "$XAI_API_KEY"
.venv/bin/python src/run_proof.py
```

Requires `XAI_API_KEY` (or another provider via `letta connect`). Do not purchase anything.

Headless one-shot:

```bash
.venv/bin/letta --backend local --agent <id> --new -p "Who are you?" --output-format json
```

## Communication honesty

| Path | Used? | Class |
|---|---|---|
| REST `send_message_to_agent_and_wait_for_reply` / Groups supervisor | No | Native Letta Server/Cloud A2A — **not in this install** |
| Letta Code **Agent tool** (subagents) | Attempted in test 2 | Parent/subagent, harness-native |
| `letta -p --from-agent` | Yes in tests 2b and 5 | Harness reminder, still parent-routed |
| Python sequential prompts | Yes, labelled | **Custom routing. Not native A2A** |
| Shared MemFS block | No | Private MemFS per agent |

If a transcript shows Sabi *speaking as* Arthur, that is impersonation, not collaboration.

## Files

See `MANIFEST.md`. Evidence after a run is under `evidence/`.

## Verdict lives in `evidence/VERDICT.md` after the suite finishes.
