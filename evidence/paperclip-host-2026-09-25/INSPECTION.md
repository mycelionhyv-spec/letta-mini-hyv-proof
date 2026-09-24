# Host inspection — Paperclip trial attempt — 2026-09-25

Status: **NOT READY**. No specialist was run through Paperclip. No company was imported. `main` was not modified.

## What this host actually has

Letta Code 0.32.15 local backend. One agent record and one MemFS namespace:

| Name on disk | Id | Role on disk | In Paperclip? |
|---|---|---|---|
| Edwin | `agent-local-b867273f-b849-40de-b616-e5cf9b45239b` | Money & Commitments | No. Preserved. Not the research Edwin. |

`letta --backend local agents list` returned only that id. Provider auth exists on the host and was not copied.

## Canonical specialist ids from `codex/five-agent-proof-verification` at `b145a41`

Each was asked with `letta --backend local --agent <id>`. The CLI returned `Agent <id> not found`. No MemFS directory exists for any of them.

| Worker | Role | Id | This host |
|---|---|---|---|
| Arthur | Technology & Systems | `agent-local-453f42d0-f174-4046-892e-0ce2b5c2ae2e` | absent |
| Mr G | Creative & Experience | `agent-local-bc3abe43-c523-41d1-b433-261ea1697306` | absent |
| Edwin | Research & Analysis | `agent-local-738aaad8-bf19-4151-bd2c-999770104147` | absent |
| Agnes | Finance & Business Operations | `agent-local-29dd7050-8717-4f99-b0ae-0f6b657fb104` | absent |
| Cyber | Cyber Security | none | not created here |
| Sabi | Coordinator, excluded | `agent-local-df17783d-ebc0-4fb7-8d8e-7b11f603fb81` | absent, and stays out of Paperclip |

## Why Cyber was not minted here

The only store on this machine is the money-Edwin backend. A new Cyber id would not share a store with Arthur, Mr G, Edwin Research or Agnes. That would be a third split, not one team.

## Blind isolation and namespace inspection

| Check | Result |
|---|---|
| Fresh blind private-memory test | **BLOCKED**. The original five namespaces are not on this host. The runner was not started, so it could not teach markers into the wrong Edwin. |
| Read-only namespace inspection | **DONE, and it does not show five-way isolation**. One namespace directory exists, named exactly `agent-local-b867273f-b849-40de-b616-e5cf9b45239b`, with `memory/system/persona.md`. The five canonical ids have no directory. See `namespace-inspection.json`. Directory presence is not a cryptographic isolation proof. |
| Paperclip smoke tasks | **NOT RUN**. There is no Paperclip company and no resolved worker. |

## Paperclip

Not installed and not started.

- This machine's Node is v22.23.2. Paperclip's own local-development doc requires Node.js 24.11+.
- Latest GitHub release seen while inspecting: `paperclipai/paperclip` tag `v2026.916.1` (2026-09-21).
- Process adapter contract read from that tree: `adapterType` `process`, config `command` / `args` / `cwd` / `env` / `timeoutSec` / `graceSec`. Runtime env always set by current `execute.ts`: `PAPERCLIP_AGENT_ID`, `PAPERCLIP_COMPANY_ID`, `PAPERCLIP_API_URL`, `PAPERCLIP_RUN_ID`, and `PAPERCLIP_API_KEY` when a run token exists. `PAPERCLIP_TASK_ID` is set by the ACP engine, not by `server/src/adapters/process/execute.ts`. The bridge refuses to guess a task when `PAPERCLIP_TASK_ID` is missing.
- Company import was not executed. A hand-authored package is in `paperclip/company/` and is marked not imported. Heartbeats were not enabled.

## Quickest safe fix

Run this same branch on the machine whose `~/.letta/lc-local-backend/agents` still contains `agent-local-738aaad8-bf19-4151-bd2c-999770104147` (Edwin Research) plus Arthur, Mr G and Agnes. Do not copy those stores into this sandbox and do not recreate them with new ids. On that host: create Cyber, set `resolved: true` only after each id answers, install Paperclip with Node 24.11+ bound to loopback, dry-run the company import with `pauseAutomations: true`, then run one synthetic smoke per specialist.
