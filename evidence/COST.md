# Cost ledger — live run 2026-09-21

| Item | Who billed | Amount |
|---|---|---|
| Letta Code 0.32.15 local backend | Letta | **$0** (Apache / local, no account) |
| Letta Cloud free tier (3 managed agents, rotating models) | Letta | **Not used** — no `LETTA_API_KEY` |
| Letta credits / LLM gateway | Letta | **$0** |
| Model | xAI Grok 4.3 via existing `XAI_API_KEY` | BYOK. Not purchased for this test |
| OpenAI embeddings | — | Not used |
| Docker / Postgres | — | Not used (pip Letta Code + local MemFS) |

## Token counts from the 17 headless calls

| | Tokens |
|---|---|
| Prompt | 417,209 |
| Completion | 3,350 |
| Total reported | 605,206 |

Prompt bloat is the Letta Code system prompt (~21k tokens per short identity answer). That is a real cost driver if you scale departments.

No second Letta account was created. Nothing was purchased.
