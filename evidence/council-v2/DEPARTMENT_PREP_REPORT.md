# Council V2 — Arthur and Mr G department prep

Branch: `council/v2-control-plane`  
PR: [#1](https://github.com/mycelionhyv-spec/letta-mini-hyv-proof/pull/1) (not merged)  
Class: custom receipt-backed routing. **Not native Letta A2A.**  
Sabi persona was not rewritten.

## Agent IDs

| Agent | Role | ID |
|---|---|---|
| Arthur | Technology & Systems | `agent-local-453f42d0-f174-4046-892e-0ce2b5c2ae2e` |
| Mr G | Creative & Experience | `agent-local-bc3abe43-c523-41d1-b433-261ea1697306` |
| Sabi (unchanged) | Coordinator / only interface | `agent-local-df17783d-ebc0-4fb7-8d8e-7b11f603fb81` |

## Validations

| # | Check | Result | Evidence |
|---|---|---|---|
| 1 | Identity in a new conversation | **PASS** | [01-identity-arthur.json](departments/01-identity-arthur.json), [01-identity-mrg.json](departments/01-identity-mrg.json) |
| 2 | Recall brand / Council V2 facts in a new conversation | **PASS** | [02-facts-arthur.json](departments/02-facts-arthur.json), [02-facts-mrg.json](departments/02-facts-mrg.json) |
| 3 | Arthur rejects ungrounded marketing copy | **PASS** | [03-arthur-rejects-marketing.json](departments/03-arthur-rejects-marketing.json) |
| 4 | Mr G labels technical claims as needing Arthur | **PASS** | [04-mrg-labels-technical.json](departments/04-mrg-labels-technical.json) |
| 5 | Isolation: Mr G does not know `LATTICE-77`; Arthur does not know `AMBER-14`; each recalls their own | **PASS** | [05-isolation-*.json](departments/), [05-own-code-*.json](departments/) |
| 6 | One bounded Council V2 run; Sabi cites both receipt IDs | **PASS on second attempt** | [council-reflection-v1.json](council-reflection-v1.json) |
| 7 | Evidence saved on V2 branch only | **PASS** | this folder |
| 8 | Offline contract tests | **PASS** (4/4) | `python -m unittest tests/test_council.py` |

First live council attempt **failed closed**: Sabi did not copy `[receipt:…]` tags. That run was not persisted (failure persistence was added afterwards). Second run listed the exact tags in the **runner prompt** (not a Sabi persona edit) and Sabi cited `rcpt-fb7f0eaf1b55` and `rcpt-05accd07149b`.

## Files changed (this task)

- `src/council.py` — persist fail-closed records; runner lists exact receipt tags for Sabi to copy
- `src/run_department_prep.py` — live department validations
- `src/run_council_v2.py`, `tests/test_council.py`, `docs/COUNCIL_V2.md` — already on the V2 branch; present locally
- Arthur / Mr G **MemFS only** (`persona.md`, `brand.md`, `private.md`). Sabi MemFS untouched.
- `evidence/council-v2/**`

## Cost

| | |
|---|---|
| Letta Cloud | not used |
| Purchases | none |
| New agents | none |
| Offline tests | 0 model calls |
| Department prep | 10 live Grok 4.3 calls |
| Council attempt 1 | 3 calls, citation fail, not persisted |
| Council attempt 2 | 3 calls, **67,332** reported tokens |
| Routing | custom parent process |

BYOK xAI. Not Letta credits. Prompt bloat remains ~21k system tokens per short reply.

## Remaining weakness

- Sabi still does not cite receipts unless the runner **lists the exact tags**. Personality is not receipt discipline.
- Mr G still emits a “Technical Recommendation” block (AES-256) even while saying “confirm with Arthur”. Labelled, but not fully staying in creative scope.
- First fail-closed council run was not saved; only the passing second run is auditable.
- Isolation is MemFS-private facts, not a cryptographic barrier.

## Recommendation

**READY FOR THREE LIVE COUNCIL TESTS**

Departments now have distinct private roles, durable facts, and isolation. The control plane fail-closed when Sabi skipped tags, then passed when tags were listed. That is enough to run three bounded live requests on this branch. It is **not** a website integration, **not** native A2A, and **not** a Sabi rewrite.
