# Verdict

**CONDITIONAL — valuable for memory and identity. Not a drop-in MyHYv agent foundation.**

This is a live run, not a blueprint. Transcripts are in this folder.

## Tests

| Test | Result | Evidence |
|---|---|---|
| 1 Identity | **PASS** | Three voices stayed in role. Arthur refuses marketing copy. Mr G names feeling first. Sabi refuses to implement. `01-identity-*.json` |
| 2 Native A2A | **FAIL** | Sabi produced a “Both departments have responded” brief **without** calling the Agent tool (`tools_seen: []`). That is impersonation, not collaboration. `02-communication-sabi-scenario.json` |
| 2b Custom routing | **PASS (labelled)** | Python asked Arthur, then Mr G, then Sabi. `--from-agent` only injects a harness reminder. Distinct work came back. `02b-*.json` |
| 3 Memory after new conversation | **PASS** | GOLDROOT, IRONSPINE, VELVETKEY all recalled from MemFS files the agents wrote. `03-memory-read-*.json` + `system/departmental*.md` |
| 4 Shared context | **PASS (isolation)** | Mr G: “I do not know.” Private MemFS. No shared block was attached. `04-shared-context.json` |
| 5 Conflict | **PASS (via custom routing)** | Mr G pitched always-on home capture. Arthur: **No.** Sabi sided with Arthur on risk and rejected empty compromise. `05-conflict-*.json` |
| 6 Integration | **No drop-in** | Current LifeOS has no Sabi UI, no Gemini adapter, Join is not auth, Capture approve is not a departmental receipt. `src/integration_map.md` |
| 7 Cost | **Not Letta free tier** | Letta Code local = $0. 17 Grok 4.3 calls, ~605k total tokens BYOK. See `COST.md` |

## What Letta actually supplied

Worked:

- Persistent **agent ids**
- **MemFS** identity (`persona.md`) and facts that survive `--new` conversations
- Default **memory isolation** between agents
- A real model behind each mouth (not canned strings)

Did not supply on this install:

- Native `send_message_to_agent_*` / Groups supervisor
- A guarantee that Sabi will *delegate* instead of *impersonate*
- Letta Cloud free-tier managed agents (no `LETTA_API_KEY`)
- Shared memory unless we attach it ourselves

## Communication classes (do not conflate)

1. **Native A2A (Letta Server/Cloud tools/Groups)** — not exercised. Not present in Letta Code local.
2. **Parent/subagent (Letta Code Agent tool)** — attempted. Sabi did not use it in the scenario turn.
3. **Shared-memory collaboration** — not attached. Isolation held.
4. **Custom routing** — what actually produced the team scenario and the conflict test.

## Hours to use the successful parts

| Work | Hours | Notes |
|---|---|---|
| Sabi-only chat route + MemFS identity | 16–24 | New UI. Do not reuse deleted Sabi panel |
| Custom department router (Sabi → Arthur/Mr G → Sabi) | 12–20 | You own orchestration. Letta does not |
| Owner auth + receipts | 20–32 | Join is not auth. Capture approve is a different contract |
| Switch to Letta Cloud Groups for native A2A | 16–24 + account | Requires `LETTA_API_KEY`; still must stop impersonation |
| Wire mock adapter / Capture | 8–12 | Complementary, not a Letta feature |

Rough **48–80 hours** to put identity+memory+a labelled router behind a real Sabi surface. Native “the team talks to itself” is **not** in that number until Cloud/Server Groups are proven separately.

## What still needs custom development

- Delegation policy so Sabi cannot speak for Arthur
- Departmental receipts
- Owner authentication
- Any Gemini adapter (absent in this frontend)
- Cost controls (21k prompt tokens of Letta system text per short reply)
