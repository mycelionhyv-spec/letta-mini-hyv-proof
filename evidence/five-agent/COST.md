# Cost ledger — five-agent run 2026-09-22

| Item | Who billed | Amount |
|---|---|---|
| Letta Code local backend | Letta | **$0** |
| Letta Cloud free tier | Letta | **Not used** |
| New Letta account / credits | — | none |
| Extra purchases | — | none |
| Model | xAI Grok 4.3 via existing `XAI_API_KEY` | BYOK |
| New agents created | Edwin, Agnes (local only) | $0 |

## Reconciled usage from the 28 archived headless calls

| | Tokens |
|---|---|
| Prompt | 684,557 |
| Completion | 6,555 |
| Cached input (separate field) | 59,648 |
| Total reported | 750,760 |

For **every call**, Letta's `usage.total_tokens` equals `prompt_tokens + completion_tokens + cached_input_tokens`. The previous ledger omitted cached input from the component rows. `context_tokens` totals 620,828 across the same records and is recorded separately; it must not be added to the total. [Per-call raw-field reconciliation](token-reconciliation.json) is generated and checked by `python3 src/reconcile_usage.py --check` from the repository root.

These are Letta's reported usage fields. They do not prove which tokens xAI billed at which cache rate. No provider invoice or pricing record is present, so **actual monetary cost is unknown**. A model credential was not available in the verification workspace; no new model calls were made.

Prompt bloat is still the Letta Code system prompt (~21k–24k tokens per short reply). Five departments make that worse, not better.

No second Letta account was created. Nothing was purchased. Native A2A was not enabled.
