// Body assembly copied from Paperclip server/src/adapters/http/execute.ts
// (master, read 2026-09-25). The HTTP adapter posts agentId, runId, and the
// heartbeat context. It does not choose a task itself.
const url = process.env.BRIDGE_URL;
const payloadTemplate = {};
const agent = { id: process.env.AGENT_ID };
const runId = process.env.RUN_ID;
const context = JSON.parse(process.env.WAKE_CONTEXT || "{}");
const body = {
  ...payloadTemplate,
  agentId: agent.id,
  runId,
  context,
};
const response = await fetch(url, {
  method: "POST",
  headers: {
    "content-type": "application/json",
    ...(process.env.BRIDGE_TOKEN ? { "X-MyHYv-Bridge-Token": process.env.BRIDGE_TOKEN } : {}),
  },
  body: JSON.stringify(body),
});
const text = await response.text();
process.stdout.write(JSON.stringify({ status: response.status, body: text }));
if (!response.ok) process.exit(2);
