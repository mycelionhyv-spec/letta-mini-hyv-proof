# MyHYv Paperclip company package — NOT IMPORTED

This directory is the configuration that would be submitted to Paperclip on the host that actually holds Arthur, Mr G, Edwin Research and Agnes.

It was **not** imported. Paperclip is not running here. Do not treat `manifest.json` as a successful company.

Import rules once that host is available:

1. Bind Paperclip to loopback only. Do not publish the UI or API.
2. Preview with `POST /api/companies/import` is wrong for an existing server; use the preview/apply routes on a new company target with `pauseAutomations: true`.
3. Current Paperclip import forces timer heartbeats off. Leave them off. Do not enable schedules in this trial.
4. Replace `adapterConfig.cwd` with the absolute checkout path of this repo on that host before apply. The process adapter executes `command` directly.
5. Do not put `PAPERCLIP_API_KEY`, `XAI_API_KEY`, or Letta provider auth in this package. The run token is minted by Paperclip. The Letta provider config stays in the local Letta store.
6. Sabi is not in this package.
7. The money-Edwin id is not in this package.
8. Cyber's `letta_id` is null until that host creates him and a live identity reply is recorded. The bridge will fail closed until `config/paperclip-roster.json` says `resolved: true`.

`manifest.json` fields match `portabilityAgentManifestEntrySchema` as read from Paperclip `packages/shared/src/validators/company-portability.ts` on master while preparing this branch. It was not dry-run through the importer, so it is not a verified import.
