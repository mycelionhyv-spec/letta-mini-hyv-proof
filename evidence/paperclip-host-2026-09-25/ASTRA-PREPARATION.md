# Astra preparation checkpoint — 2026-09-25

**BLOCKED ON ACCESS. No live Paperclip dispatch or specialist model call ran.**

This check was made in the Work Mode workspace, a different environment from the
earlier `STORE-SEARCH.md` inspection. That earlier report's Money Edwin was on
the earlier machine; it is not evidence of an agent store on this workspace.

## Verified here

- Draft PR #4 was open at `4074df60e4c1e4f6daac2164c720cfa32d5a5176` before these
  changes. Base is `codex/five-agent-proof-verification`; `main` is unchanged.
- Node is 24.19.0, sufficient for the reviewed Paperclip requirement 24.11.0+.
- No Letta or Paperclip executable, default local store, or configured remote
  SSH host was found in this workspace. Environment checks found no configured
  XAI, Letta, Paperclip or bridge token in the named variables. Values were not
  printed. Other hosts' provider configuration cannot be inferred from this.
- Accessible saved-file searches for Letta, agents, backups, the store name and
  the Research Edwin ID found no restorable store. The prior host's wider search
  remains recorded separately. This does not prove all of Michael's computers
  or unconnected backups lack the original memories.
- Paperclip release `v2026.916.1` and Letta Code `v0.32.15` sources were inspected
  for the real HTTP payload, private endpoint guard, header handling, CLI flags,
  tool filtering and local store layout.

## Changes prepared and tested

- Authenticated wakes reject missing, wrong or duplicate token headers before
  body reads, issue lookup or model invocation; authorized body size is bounded.
- The Paperclip ID must map to exactly one worker; each Letta identity is unique
  and cannot match either excluded identity. Only runnable trial states pass.
- A cross-process lock serializes invocation. The attempt is durably reserved
  before invoking Letta. A crash, uncertain result or failed receipt write cannot
  cause an unnoticed repeat call.
- Results have private atomic receipts tying output and usage to company, task,
  run and both agent IDs. This is necessary because the pinned Paperclip HTTP
  adapter discards successful response bodies.
- Letta runs with empty tools, all skills off, mods off, strict permissions and
  reflection off. Bridge/Paperclip credentials are removed from the child
  environment. Raw provider exception/stderr details are not written to receipts.
- Host-only roster, read-only inventory, protected environment templates,
  Linux user-service template, pinned installation procedure and loopback
  allowlist are prepared. They are not installed services.

Validation: `python -m unittest discover -s tests -v`: **32 tests passed**.
These are offline tests, including local HTTP transport with a fake issue API
and fake Letta executable. They are not a real Paperclip dispatch or a live
identity/memory isolation test. Syntax checks and `git diff --check` also passed.
The preflight correctly exits 2 with `BLOCKED` on this workspace.

## Remaining live gates

| Gate | Result |
| --- | --- |
| Persistent private host and authenticated owner | Not available here |
| Five responding, role-verified Letta identities | Unverified; checked-in roster stays unresolved |
| Original memory restoration | No accessible backup found; not restored |
| Paperclip install/company import | Not run |
| Real smoke receipts | None |
| Provider usage/cost | No trial calls made; no live cost receipt |
| Owner website/Sabi task-result route | Unimplemented and not exercised |

**One owner-controlled input needed:** authenticated terminal access to Michael's
persistent deployment computer/server with its existing authorized Letta/provider
configuration. Once connected, inspect and back up the store; restore identities
if available, otherwise perform the explicitly authorized fresh rebuild with new
IDs. No replacement identities or stores have been silently created here.

Next executable inventory: `python3 src/paperclip_preflight.py --store /confirmed/store`.
The complete host procedure is in `docs/paperclip-host-deployment.md`. Keep PR #4
draft and all worker schedules, external actions and customer access disabled.
