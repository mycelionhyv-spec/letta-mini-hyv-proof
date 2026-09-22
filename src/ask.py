"""Headless Letta Code client. One persistent agent, one prompt, JSON transcript."""

from __future__ import annotations

import json
import os
import subprocess
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
LETTA = ROOT / ".venv" / "bin" / "letta"
EVIDENCE = ROOT / "evidence"


def ask(
    agent_id: str,
    prompt: str,
    *,
    new_conversation: bool = True,
    from_agent: str | None = None,
    timeout: int = 240,
    extra: list[str] | None = None,
) -> dict[str, Any]:
    """Send one prompt. Returns parsed JSON plus raw stdout/stderr/timing.

    Communication class for this helper: parent process → Letta Code CLI → one agent.
    That is NOT native agent-to-agent. Native A2A would appear as Agent-tool calls
    inside the returned transcript.
    """
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    cmd = [
        str(LETTA),
        "--backend",
        "local",
        "--agent",
        agent_id,
        "-p",
        prompt,
        "--output-format",
        "json",
        "--reflection-trigger",
        "off",
        "--no-bundled-skills",
        "--no-mods",
        "--no-system-info-reminder",
    ]
    if new_conversation:
        cmd.append("--new")
    if from_agent:
        cmd.extend(["--from-agent", from_agent])
    if extra:
        cmd.extend(extra)

    t0 = time.time()
    proc = subprocess.run(
        cmd,
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        timeout=timeout,
        env={**os.environ, "CI": "1", "NO_COLOR": "1"},
    )
    elapsed = round(time.time() - t0, 2)
    raw = proc.stdout or ""
    parsed: Any = None
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        # stream-json / mixed logs: take last JSON object
        for line in reversed(raw.splitlines()):
            line = line.strip()
            if line.startswith("{") and line.endswith("}"):
                try:
                    parsed = json.loads(line)
                    break
                except json.JSONDecodeError:
                    continue
    return {
        "agent_id": agent_id,
        "prompt": prompt,
        "new_conversation": new_conversation,
        "from_agent": from_agent,
        "elapsed_s": elapsed,
        "returncode": proc.returncode,
        "parsed": parsed,
        "stdout": raw,
        "stderr": proc.stderr,
        "cmd": cmd,
    }


def text_of(result: dict[str, Any]) -> str:
    p = result.get("parsed")
    if isinstance(p, dict):
        for k in ("result", "text", "message", "content", "assistant"):
            v = p.get(k)
            if isinstance(v, str) and v.strip():
                return v
        msgs = p.get("messages") or p.get("items") or []
        chunks: list[str] = []
        if isinstance(msgs, list):
            for m in msgs:
                if not isinstance(m, dict):
                    continue
                role = str(m.get("role") or m.get("type") or "")
                if role in {"assistant", "result", "agent"}:
                    c = m.get("content") or m.get("text") or m.get("message")
                    if isinstance(c, str):
                        chunks.append(c)
                    elif isinstance(c, list):
                        for part in c:
                            if isinstance(part, dict) and part.get("text"):
                                chunks.append(str(part["text"]))
                            elif isinstance(part, str):
                                chunks.append(part)
        if chunks:
            return "\n".join(chunks)
        if p.get("error"):
            return str(p["error"])
    return (result.get("stdout") or "")[-4000:]


def tool_names(result: dict[str, Any]) -> list[str]:
    names: list[str] = []
    blob = json.dumps(result.get("parsed") or result.get("stdout") or "")
    for needle in (
        "Agent",
        "send_message_to_agent",
        "send_message_to_agent_and_wait_for_reply",
        "send_message_to_agents_matching_all_tags",
        "Task",
        "memory",
    ):
        if needle in blob:
            names.append(needle)
    return names
