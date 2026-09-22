# MYHYV — Letta Mini-HYV working proof

Disposable test: can Letta hold **identity, memory, delegation and disagreement** for three MyHYv agents?

This is **not** a website change. The LifeOS frontend was inspected read-only and was not edited.

**Verdict: CONDITIONAL.** Memory and identity work. Native agent-to-agent does not, on this install.

## What actually ran

| Layer | What we used | Cost |
|---|---|---|
| Agent runtime | **Letta Code 0.32.15**, `--backend local`, MemFS on disk | $0, no Letta account |
| Cloud free tier | **Not used.** Needs `LETTA_API_KEY` | n/a |
| Native REST Groups / `send_message_to_agent_*` | **Not available** on Letta Code local | n/a |
| Models | **xAI Grok 4.3** (`xai/grok-4.3`, reasoning `none`) via BYOK | Not Letta credits |

## Agents (exactly three)

| Name | Role | Local id |
|---|---|---|
| Sabi | Coordinator. Michael's only interface | `agent-local-df17783d-ebc0-4fb7-8d8e-7b11f603fb81` |
| Arthur | Technology & Systems | `agent-local-453f42d0-f174-4046-892e-0ce2b5c2ae2e` |
| Mr G | Creative & Experience | `agent-local-bc3abe43-c523-41d1-b433-261ea1697306` |

## Launch

```bash
cd letta-proof   # or clone this repo
uv venv .venv
uv pip install --python .venv/bin/python letta-client letta
.venv/bin/letta backend local
.venv/bin/letta --backend local connect openai-compatible --base-url https://api.x.ai/v1 --api-key "$XAI_API_KEY"
.venv/bin/python src/run_proof.py
```

Requires an LLM key. Do not purchase anything. Recreate agents if you clone cold.

## Communication honesty

| Path | Used? | Class |
|---|---|---|
| REST `send_message_to_agent_*` / Groups | No | Native Letta Server/Cloud A2A — not in this install |
| Letta Code Agent tool | Attempted | Parent/subagent. Sabi did not call it |
| `letta -p --from-agent` | Yes | Harness reminder, still parent-routed |
| Python sequential prompts | Yes, labelled | **Custom routing. Not native A2A** |

If a transcript shows Sabi speaking *as* Arthur, that is impersonation, not collaboration. See `evidence/02-communication-sabi-scenario.json`.

Live verdict: `evidence/VERDICT.md`
