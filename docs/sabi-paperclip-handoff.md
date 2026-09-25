# Sabi to Paperclip handoff — for Astra, not implemented

Sabi stays out of Paperclip. She is not a worker in `config/paperclip-roster.json` and she is not in the company package.

The current MyHYv site was not changed and was not tested against Paperclip. Do not say Sabi is live on the site.

## Later owner-area contract

The private owner area may later create and review tasks only through a server-side bridge:

1. The browser calls the site's own owner route. It never receives `PAPERCLIP_API_KEY`, a Letta id, or the Paperclip base URL.
2. The server checks an owner session. Signed-out requests are rejected.
3. The server sends a task to the loopback Paperclip API with a server-held credential.
4. Allowed task types are `synthetic-smoke` and, for Cyber only, `security-review-readonly`.
5. The server stores the bridge result id, input hash, output hash, status and usage fields. It does not store the Paperclip token or Letta memories.
6. If Paperclip is not on a private route the site server can reach, the owner route returns unavailable. It does not fall open.

## Current limitation

This host cannot verify that path. Paperclip is not installed, the canonical Letta agents are not here, and no owner route was exercised.

Astra's next action, on the machine that holds the original Letta store and a loopback Paperclip: implement the server route above and test signed-out rejection plus one labelled synthetic task that never reaches the browser with credentials.
