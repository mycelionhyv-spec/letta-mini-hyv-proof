# Private five-worker deployment — prepared, not deployed

The accessible Work Mode workspace is not a persistent worker host. No live task has
run here. PR #4 remains a draft; do not merge it to claim completion.

## Pinned runtime and compatibility findings

Target Paperclip **v2026.916.1**, released 2026-09-21, Node **24.11.0 or newer**.
The bridge CLI flags and store layout were reviewed against Letta Code **v0.32.15**.
Do not upgrade an existing Letta store without a complete private backup. Preserve
its current provider/model; the historical proof used `xai/grok-4.3`.

- Paperclip's HTTP adapter sends `agentId`, `runId`, and `context`. It does not
  pass a per-run API key to this bridge automatically. Provision a protected
  credential with only the issue-read authority required for the trial.
- It uses `timeoutMs`. The company package allows 240 seconds, covering the
  bridge's 20-second issue lookup and 180-second Letta subprocess timeout.
- It does **not read the successful response body**. The bridge now saves a
  private durable receipt containing the result and usage. Paperclip's generic
  HTTP success log is not itself a worker result or a cost receipt.
- Its private endpoint guard requires the exact origin in
  `PAPERCLIP_HTTP_ADAPTER_PRIVATE_ENDPOINT_ALLOWLIST` on the Paperclip process.
  Use only `http://127.0.0.1:8765`, not a wildcard or a `/wake` path.
- `adapterConfig.headers` contains literal strings in this release. Do not use
  a fake environment or secret-reference placeholder as an authentication token.

Primary source references:
[release](https://github.com/paperclipai/paperclip/releases/tag/v2026.916.1),
[HTTP adapter](https://github.com/paperclipai/paperclip/blob/v2026.916.1/server/src/adapters/http/execute.ts),
[private endpoint guard](https://github.com/paperclipai/paperclip/blob/v2026.916.1/server/src/adapters/http/remote-fetch.ts),
[installation](https://github.com/paperclipai/paperclip/blob/v2026.916.1/doc/INSTALLING.md),
[deployment modes](https://github.com/paperclipai/paperclip/blob/v2026.916.1/doc/DEPLOYMENT-MODES.md),
[Letta CLI arguments](https://github.com/letta-ai/letta-code/blob/v0.32.15/src/cli/args.ts),
[Letta tool filter](https://github.com/letta-ai/letta-code/blob/v0.32.15/src/tools/filter.ts).

## Host and identity gate

1. Connect to Michael's existing persistent Linux/macOS host (or WSL with a
   persistent local filesystem) with its authorized provider connection.
   No new subscription or provider substitution is authorized.
2. Run `python3 src/paperclip_preflight.py --store /confirmed/store` read-only.
   This does not invoke Letta, inspect private memory text, authenticate a provider,
   or mark file presence as a recovered identity.
3. Back up the **entire** store and its relevant configuration into a private
   location before any runtime invocation that might migrate it. Keep original
   files in place. For this Letta version the default store is
   `~/.letta/lc-local-backend`; `LETTA_LOCAL_BACKEND_DIR` overrides it. Agent records
   are `agents/<id>.json`; memories are `memfs/<id>/memory`.
4. Verify Arthur, Mr G, Research Edwin and Agnes against runtime metadata, role,
   model and distinct namespaces. Canonical IDs are in `config/paperclip-roster.json`.
   Repository evidence is not a runtime identity check. Sabi and Money Edwin
   remain excluded even if found on the selected machine.
5. If the original records cannot be recovered from accessible hosts/backups,
   create **new** identities in a new, explicitly named team store on the chosen
   persistent host. Do not replace the old store. Use the saved role definitions
   in `paperclip/company/agents/*/AGENTS.md` and the Edwin/Agnes personas in
   `config/personas/`. Arthur and Mr G's saved definitions are minimal; record
   that limitation. Never load old transcript answers as restored private memory.
   Create Cyber separately. Record original ID, new ID, role, namespace, model,
   creation date and `original_memories_restored: false`. Do not preassign fake IDs.

## Install, pause and configure

On the persistent host, the pinned managed install entry point is:

```sh
npx --registry https://registry.npmjs.org paperclipai@2026.916.1 install --version 2026.916.1
paperclipai onboard --yes --no-install-service
paperclipai configure --section server
```

Use custom server configuration to select **authenticated/private** and
**loopback**. Default quickstart is local-trusted and has no user login; that is
not the final owner-access setup. Complete Michael's owner bootstrap privately,
check `paperclipai doctor`, and verify both actual listener addresses and
signed-out API rejection. Do not bind to `0.0.0.0` or create a public proxy.
Use a private tunnel for owner access if already available. Do not create a
second public login route on the website.

Only after all five Letta identities are confirmed, preview the company import
against this exact release. Import with automations paused, keep every worker
paused, and verify actual stored heartbeat/wake settings. The package has not
yet been accepted by a real importer. If the schema differs, adapt the local
package and repeat the preview before import.

Create an owner-only directory (mode 0700) outside the repo for the actual roster,
environment and ledger. Copy the checked-in roster there, fill the actual
Paperclip IDs and verified Letta IDs, and only then set those workers resolved.
Set `MYHYV_BRIDGE_ROSTER` to that file. Never mutate the checked-in unresolved
roster to claim this workspace is live.

Use `paperclip/deploy/*.env.example` as templates. Generate a high-entropy token
on the host and store it only in the protected bridge environment and each
worker's local Paperclip HTTP header `X-MyHYv-Bridge-Token`. Verify that only the
owner can inspect token-bearing adapter settings and that exports do not retain
the value. Do not export populated adapters into Git. If those permissions
cannot protect it, keep workers paused and replace the auth mechanism first.

Install Paperclip's supported background service and the bridge service under
the correct owner account with a restrictive umask. The provided Linux bridge
unit is a template, not an installed service. Verify the service's actual Node
and Letta executables, provider configuration and persistent data paths, then
restart both services once before the trial. Use a local filesystem for the
ledger: cross-process `flock` is required; NFS and native Windows are unsupported.

## Bounded real trial and receipts

The bridge starts only with authentication configured. It rejects missing,
incorrect or duplicate token headers before reading the wake body. An authorized
wake must identify one task and exactly one pinned worker. The fetched task must
belong to the configured company, be assigned to that worker, have a permitted
type, and be `todo` or `in_progress`.

Letta is invoked with tools disabled (`--tools ''`), all skills disabled,
mods disabled, strict permissions, and reflection off. The model subprocess
does not receive bridge or Paperclip credentials. This is a bounded text-only
trial; it does not grant the workers deployment, publishing or customer access.

Create one synthetic issue per worker with the `synthetic-smoke` label and an
explicit assignee. Suggested text: "Identify your own name and specialist role.
Return one short observation about how your role contributes to this team.
Do not use tools, recall private facts, or take external action."

Use the **real Paperclip dispatch path**, one worker at a time. If the pinned
release requires manual on-demand wake permission, enable only that permission
for the selected worker during its trial, then pause it again. Scheduled,
assignment and automation wakes remain disabled. Do not use the test adapter
helper or fake Letta executable as live proof.

Each receipt contains company, task, run, Paperclip worker, Letta ID, result,
input/output hashes and available usage. Verify it against the real Paperclip
run record and the intended Letta agent. Review the bounded output before
attaching it to the owner-visible task. Raw private memories, provider keys
and unfiltered runtime logs must not be attached. Until that result is attached,
Paperclip's generic HTTP success summary alone does not show the worker answer.
The bridge does not mark the issue done or submit Paperclip cost events.

Negative checks must cover wrong worker, invalid/missing token, unresolved ID,
duplicate wake and uncertain execution. Verify lookup and Letta are untouched
by unauthorized wakes. An interrupted/uncertain attempt stays reserved and is
not automatically retried. Preserve the ledger when restarting services. Never
delete it to force a retry; investigate the provider/run outcome first.

At most one Letta CLI invocation per task is enforced, not a provider-wide
monetary cap. Record actual provider usage/cost if exposed; otherwise write
"unknown", never zero. No smoke calls have been made by this preparation.

Keep all workers paused after the trial until Michael authorizes broader work.
The owner website route remains a separate unimplemented contract in
`docs/sabi-paperclip-handoff.md`. Report Sabi as connected only after an
authenticated owner task-and-result path has been exercised successfully.
