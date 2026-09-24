# MyHYv Paperclip company package — NOT IMPORTED

This package was not imported. Paperclip is not running here, and the canonical Letta agents were not found on this host. Do not apply it until those agents answer on the backend Paperclip will call.

Task handoff: `adapterType` is `http`, not `process`.

Paperclip's process adapter (`server/src/adapters/process/execute.ts`) does not read the heartbeat context and does not set a task id. Its HTTP adapter (`server/src/adapters/http/execute.ts`) POSTs `agentId`, `runId`, and the heartbeat `context`. The bridge accepts a task id only from `context.taskId` or `context.issueId`, and only when they agree. It then fetches that issue and checks the company and assignee. It does not list or guess tasks.

The loopback URL in this package is a placeholder (`127.0.0.1:8765`). It was not contacted by a real Paperclip server.

Sabi is not in this package. The money-Edwin id is not in this package. Cyber has no Letta id yet. Heartbeats in `runtimeConfig` stay off. `pauseAutomations` must be true if this is later imported. This manifest was not dry-run through the importer.
