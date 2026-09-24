# MyHYv Paperclip company package — NOT IMPORTED

This package was not imported. Paperclip is not running here, and the canonical Letta agents were not found on this host. Do not apply it until those agents answer on the backend Paperclip will call.

Task handoff: `adapterType` is `http`, not `process`.

Paperclip's process adapter (`server/src/adapters/process/execute.ts`) does not read the heartbeat context and does not set a task id. Its HTTP adapter (`server/src/adapters/http/execute.ts`) POSTs `agentId`, `runId`, and the heartbeat `context`. The bridge accepts a task id only from `context.taskId` or `context.issueId`, and only when they agree. It then fetches that issue and checks the company and assignee. It does not list or guess tasks.

The loopback URL in this package is a placeholder (`127.0.0.1:8765`). It was not contacted by a real Paperclip server.

Sabi is not in this package. The money-Edwin id is not in this package. Cyber has no Letta id yet. Heartbeats in `runtimeConfig` stay off. `pauseAutomations` must be true if this is later imported. This manifest was not dry-run through the importer.

## Bridge authentication

The bridge now refuses to start unless `MYHYV_BRIDGE_WEBHOOK_TOKEN` is set. It authenticates the `X-MyHYv-Bridge-Token` header before reading or parsing a wake body. Missing or invalid headers return 401 without querying Paperclip or invoking Letta.

The company export deliberately contains no token. Before enabling an HTTP adapter, create a high-entropy per-host token, provide it to the bridge through the host's protected environment, and add the matching header to each Paperclip agent's local adapter configuration. Paperclip's HTTP adapter accepts literal `headers`, but the reviewed adapter does not resolve secret references inside header values. Do not put the token in this repository or exported company package. Keep the token-bearing Paperclip config and host environment access restricted; rotate the token if either is exposed.
