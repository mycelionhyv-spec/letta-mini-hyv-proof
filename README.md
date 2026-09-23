# MYHYV — Letta Mini-HYV working proof

Disposable test: can Letta hold **identity, memory, delegation and disagreement** for five MyHYv agents?

This is **not** a website change. The LifeOS frontend was not edited. This branch adds Edwin and Agnes only. Sabi, Arthur and Mr G keep their original agent IDs.

## What actually ran

| Layer | What we used | Cost |
|---|---|---|
| Agent runtime | **Letta Code**, `--backend local`, MemFS on disk | $0, no Letta account |
| Cloud free tier | **Not used.** Needs `LETTA_API_KEY` | n/a |
| Native REST Groups / `send_message_to_agent_*` | **Not available** on Letta Code local | n/a |
| Models | **xAI Grok 4.3** (`xai/grok-4.3`, reasoning `none`) via BYOK | Not Letta credits |

## Agents (exactly five)

| Name | Role | Local id |
|---|---|---|
| Sabi | Coordinator. Michael's only interface | `agent-local-df17783d-ebc0-4fb7-8d8e-7b11f603fb81` |
| Arthur | Technology & Systems | `agent-local-453f42d0-f174-4046-892e-0ce2b5c2ae2e` |
| Mr G | Creative & Experience | `agent-local-bc3abe43-c523-41d1-b433-261ea1697306` |
| Edwin | Research & Analysis | `agent-local-738aaad8-bf19-4151-bd2c-999770104147` |
| Agnes | Finance & Business Operations | `agent-local-29dd7050-8717-4f99-b0ae-0f6b657fb104` |

Sabi, Arthur and Mr G were not replaced. Edwin and Agnes were added.

IDs live in `config/agents.json`. Department identities for the two new agents live in `config/personas/`. Recreate with `letta --backend local agents create` if you clone cold.

## Launch

```bash
.venv/bin/python src/run_proof.py
```

Requires `XAI_API_KEY`. Do not purchase anything. Evidence lands in `evidence/five-agent/`.

## Communication honesty

The five-agent suite uses **labelled custom Python routing**. That is not native Letta A2A, not Groups, and not autonomous collaboration.

| Path | Used? | Class |
|---|---|---|
| REST `send_message_to_agent_*` / Groups | No | Native Letta Server/Cloud A2A — not in this install |
| Letta Code Agent tool | Not used in the five-agent run | Parent/subagent |
| `letta -p --from-agent` | Yes | Harness reminder, still parent-routed |
| Python sequential prompts | Yes, labelled | **Custom routing. Not native A2A** |
| Shared MemFS block | No | Private MemFS per agent |

If a transcript shows Sabi *speaking as* a department without a real reply, that is impersonation, not collaboration.

LifeOS integration is not included. No website changes. These bots are not production-ready beyond the evidence in `evidence/five-agent/`.

## Verdict

See `evidence/five-agent/VERDICT.md`. Short version: **CONDITIONAL.** Five identities and own-memory recall were recorded. The archived isolation result is withdrawn pending a fresh blind live run and local storage inspection. Native A2A remains unproven.

## Verification checks (2026-09-23)

```bash
python3 src/reconcile_usage.py --check
python3 -m unittest discover -s tests -v
python3 src/run_blind_isolation.py
```

The first two commands are offline. The last requires the **original local Letta agent store** and its configured model credential. It generates fresh synthetic markers, runs blind cross-department prompts and saves exact prompts, responses and raw results in a new evidence directory. It labels storage isolation **UNVERIFIED** until someone also inspects the local MemFS namespaces; model responses alone cannot prove the boundary. Do not commit credentials or describe a code-only run as live proof.
