# Integration map — existing MyHYv website (READ-ONLY)

Inspected 2026-09-21. Files are the current LifeOS frontend in this workspace.
**Sabi panel, Gemini adapter, queues-and-receipts product, and workbook write-back are not present in this revision.** They were deleted as legacy experiments (see `handoff/07-astra.md`).

Do not claim a live wire. These are the actual surfaces a later Letta layer would have to grow adapters for.

## Public site

| Surface | File | What it is | Letta hook? |
|---|---|---|---|
| Home | `src/routes/index.tsx` | Brand lockup, Open LifeOS, Join | Display only |
| Products | `src/routes/products.tsx` | LifeOS / Signal Path / Vacate Ready cards | Copy, not an agent |
| Play | `src/routes/play.tsx` | Signal Path demonstration | Not an agent |
| Join | `src/routes/join.tsx` | Local form → `localStorage["lifeos.join.requests"]`. Explicitly **not auth** | Owner identity is **not** here |

## LifeOS app (`ssr: false`)

| Surface | File | What it is | Letta hook? |
|---|---|---|---|
| Shell | `src/routes/app.tsx`, `src/components/layout/app-shell.tsx` | Nav: Today, Capture, Tasks, Goals, Money, Health, Settings | A future Sabi thread could sit as a route. **No Sabi route exists.** |
| Today | `src/routes/app/index.tsx` | Derived snapshot from mock adapter | Could consume Letta summaries |
| Capture | `src/routes/app/capture.tsx` + `src/lib/capture/parse.ts` | Deterministic parser, **not a model**. Approve / reject / commit | Closest “preview → approve → execute” already in product. Letta must not pretend this is LLM capture |
| Tasks | `src/routes/app/tasks.tsx` | “Work queue” of tasks via adapter | Name collision only. Not Sabi departmental queues |
| Goals / Money / Health | `src/routes/app/goals.tsx` etc. | CRUD through adapter | Data plane, not agents |
| Settings | `src/routes/app/settings.tsx` | Name, currency, `simulateFailure`, seed/empty reset | QA lever. Not owner auth |

## Data / adapter

| Surface | File | Notes |
|---|---|---|
| Contract | `src/lib/api/types.ts` | `LifeOsAdapter` |
| Mock | `src/lib/api/mock-adapter.ts` | `localStorage` key `lifeos.mock.v2`, 280ms fake latency |
| Seed | `src/lib/api/fixtures/seed.json` | Synthetic only |
| Client export | `src/lib/api/index.ts` | `lifeOsApi` |

There is **no Gemini adapter** in this tree. Search hits for Gemini/Sabi in product code are absent; `handoff/07-astra.md` states the Sabi panel was deleted.

## Auth (platform chrome, not product)

| Surface | File | Notes |
|---|---|---|
| Providers | `src/lib/auth/providers.ts` | Grok broker: Google + X. **Not Gemini.** |
| Join | `src/routes/join.tsx` | Device-local request. Auth “owned by Astra and is not implemented here.” |

Owner authentication for a Letta-backed Sabi would have to be built. It does not exist as a product interface today.

## Preview host

| Surface | File | Notes |
|---|---|---|
| Bridge | `src/lib/preview-host-bridge.ts` | Grok preview embedder, not a business queue |
| Startup | `startup.sh` | Dev server on 8080 |

## What a later integration would actually add (not built)

1. A Sabi conversation route that calls Letta Code / Letta API, never the mock adapter.
2. A receipt object for “Sabi asked Arthur / Mr G” distinct from Capture approve/commit.
3. Owner auth before any agent sees real life data.
4. A Gemini (or other) adapter only if MyHYv still wants that model — **it is not in this frontend.**
5. Do not reuse Capture’s approve/commit as departmental execution without a new contract.

## Honest compatibility

| Claim | Result |
|---|---|
| Drop-in to current Sabi UI | **No.** UI deleted |
| Drop-in to Gemini adapter | **No.** File does not exist |
| Drop-in to Join as login | **No.** Join is localStorage |
| Talk to mock adapter | Possible later, new code, not a proof of Letta |
| Talk to Capture parser | Complementary; Capture is deterministic on purpose |
