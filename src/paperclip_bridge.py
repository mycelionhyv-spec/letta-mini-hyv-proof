#!/usr/bin/env python3
"""Fail-closed Paperclip process adapter bridge to one pinned Letta agent.

This file does not start Paperclip and does not mark a run complete unless the
Letta call returns a definite assistant result. Missing, mismatched, duplicate,
budget, timeout and unresolved-ID cases exit non-zero before any model call.
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[1]
ROSTER_PATH = ROOT / "config" / "paperclip-roster.json"
TERMINAL_STATUSES = {"done", "completed", "cancelled", "canceled", "closed"}
ALLOWED_TYPES = {
    "arthur": {"synthetic-smoke"},
    "mrg": {"synthetic-smoke"},
    "edwin": {"synthetic-smoke"},
    "agnes": {"synthetic-smoke"},
    "cyber": {"synthetic-smoke", "security-review-readonly"},
}


class BridgeError(Exception):
    def __init__(self, status: str, message: str, exit_code: int) -> None:
        super().__init__(message)
        self.status = status
        self.exit_code = exit_code


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def load_roster(path: Path | None = None) -> dict[str, Any]:
    raw = json.loads((path or ROSTER_PATH).read_text())
    if "workers" not in raw or "excluded" not in raw:
        raise BridgeError("blocked", "Roster is missing workers or excluded", 2)
    return raw


def ledger_path() -> Path:
    configured = os.environ.get("MYHYV_BRIDGE_LEDGER")
    if configured:
        return Path(configured)
    return Path.home() / ".letta" / "paperclip-bridge-ledger.json"


def read_ledger(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"runs": []}
    data = json.loads(path.read_text())
    if not isinstance(data, dict) or not isinstance(data.get("runs"), list):
        raise BridgeError("blocked", "Run ledger is unreadable; refusing to continue", 2)
    return data


def write_ledger(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(data, indent=2) + "\n")
    tmp.replace(path)


def task_type_of(issue: dict[str, Any]) -> str | None:
    metadata = issue.get("metadata") if isinstance(issue.get("metadata"), dict) else {}
    raw = metadata.get("taskType") or metadata.get("task_type")
    if isinstance(raw, str) and raw.strip():
        return raw.strip()
    labels = issue.get("labels") or issue.get("labelNames") or []
    if isinstance(labels, list):
        for label in labels:
            if isinstance(label, str) and label in {"synthetic-smoke", "security-review-readonly"}:
                return label
            if isinstance(label, dict) and label.get("name") in {"synthetic-smoke", "security-review-readonly"}:
                return str(label["name"])
    return None


def require_env(env: dict[str, str]) -> dict[str, str]:
    required = (
        "PAPERCLIP_AGENT_ID",
        "PAPERCLIP_COMPANY_ID",
        "PAPERCLIP_API_URL",
        "PAPERCLIP_API_KEY",
        "PAPERCLIP_RUN_ID",
        "PAPERCLIP_TASK_ID",
        "PAPERCLIP_WORKER_SLUG",
    )
    missing = [key for key in required if not env.get(key, "").strip()]
    if missing:
        raise BridgeError(
            "blocked",
            "Missing Paperclip context: " + ", ".join(missing)
            + ". The current process adapter does not invent a task.",
            3 if "PAPERCLIP_TASK_ID" in missing else 2,
        )
    return {key: env[key].strip() for key in required}


def validate_issue(issue: dict[str, Any] | None, ctx: dict[str, str], slug: str) -> str:
    if not isinstance(issue, dict) or not issue.get("id"):
        raise BridgeError("blocked", "Paperclip returned no task", 3)
    if issue.get("id") != ctx["PAPERCLIP_TASK_ID"]:
        raise BridgeError("blocked", "Fetched task id does not match PAPERCLIP_TASK_ID", 2)
    if issue.get("companyId") != ctx["PAPERCLIP_COMPANY_ID"]:
        raise BridgeError("blocked", "Task belongs to a different company", 2)
    if issue.get("assigneeAgentId") != ctx["PAPERCLIP_AGENT_ID"]:
        raise BridgeError("blocked", "Task is not assigned to this Paperclip worker", 2)
    status = str(issue.get("status") or "").lower()
    if status in TERMINAL_STATUSES:
        raise BridgeError("blocked", f"Task is already {status}", 4)
    kind = task_type_of(issue)
    allowed = ALLOWED_TYPES.get(slug)
    if allowed is None or kind not in allowed:
        raise BridgeError("blocked", "Task type is missing or not allowed for this worker", 2)
    return kind


def resolve_worker(roster: dict[str, Any], slug: str) -> dict[str, Any]:
    if slug in roster.get("excluded", {}):
        raise BridgeError("blocked", f"{slug} is excluded from Paperclip", 2)
    worker = roster.get("workers", {}).get(slug)
    if not isinstance(worker, dict):
        raise BridgeError("blocked", f"Unknown Paperclip worker slug: {slug}", 2)
    if worker.get("resolved") is not True or not worker.get("letta_id"):
        raise BridgeError(
            "blocked",
            f"{slug} has no verified Letta agent on this host",
            7,
        )
    return worker


def prior_attempts(ledger: dict[str, Any], task_id: str) -> list[dict[str, Any]]:
    return [row for row in ledger["runs"] if row.get("task_id") == task_id]


def bounded_prompt(slug: str, kind: str, issue: dict[str, Any]) -> str:
    title = str(issue.get("title") or "").strip()
    body = str(issue.get("description") or "").strip()
    prefix = (
        "Paperclip synthetic task. One reply only. Do not contact anyone, "
        "publish, deploy, spend, or change production settings. "
        "Do not claim this task is complete unless you state a concrete finding. "
        f"Worker={slug}. Task type={kind}.\n\n"
    )
    if slug == "cyber":
        prefix += (
            "You are Cyber. Read-only security review of access boundaries, "
            "secret handling, dependencies and security tests. Report evidence, "
            "risk and a recommended fix. Do not view customer records or secrets "
            "unless this task text already contains a specifically approved excerpt. "
            "Do not change settings.\n\n"
        )
    return prefix + f"Title: {title}\n\n{body}"


def execute(
    env: dict[str, str],
    *,
    roster: dict[str, Any],
    fetch_issue: Callable[[dict[str, str]], dict[str, Any] | None],
    invoke_letta: Callable[[str, str], dict[str, Any]],
    ledger_file: Path,
) -> dict[str, Any]:
    ctx = require_env(env)
    slug = ctx["PAPERCLIP_WORKER_SLUG"]
    worker = resolve_worker(roster, slug)
    issue = fetch_issue(ctx)
    kind = validate_issue(issue, ctx, slug)
    assert issue is not None
    ledger = read_ledger(ledger_file)
    attempts = prior_attempts(ledger, ctx["PAPERCLIP_TASK_ID"])
    if any(row.get("status") == "succeeded" for row in attempts):
        raise BridgeError("blocked", "This task already has a succeeded bridge run", 4)
    if attempts:
        raise BridgeError("blocked", "Budget stop: one model call already attempted for this task", 5)

    prompt = bounded_prompt(slug, kind, issue)
    input_hash = sha256_text(prompt)
    # Reserve the attempt before the model call so a crash cannot be retried blindly.
    attempt = {
        "task_id": ctx["PAPERCLIP_TASK_ID"],
        "run_id": ctx["PAPERCLIP_RUN_ID"],
        "worker": slug,
        "paperclip_agent_id": ctx["PAPERCLIP_AGENT_ID"],
        "letta_id": worker["letta_id"],
        "input_sha256": input_hash,
        "status": "started",
        "usage": None,
        "output_sha256": None,
        "error": None,
    }
    ledger["runs"].append(attempt)
    write_ledger(ledger_file, ledger)

    try:
        raw = invoke_letta(str(worker["letta_id"]), prompt)
    except TimeoutError as exc:
        attempt["status"] = "timeout"
        attempt["error"] = str(exc)
        write_ledger(ledger_file, ledger)
        raise BridgeError("timeout", str(exc), 6) from exc
    except Exception as exc:
        attempt["status"] = "provider_error"
        attempt["error"] = f"{type(exc).__name__}: {exc}"
        write_ledger(ledger_file, ledger)
        raise BridgeError("provider_error", attempt["error"], 6) from exc

    if raw.get("uncertain") or raw.get("returncode") not in (0, None):
        attempt["status"] = "uncertain"
        attempt["error"] = str(raw.get("error") or "Letta result was not a definite success")
        attempt["usage"] = raw.get("usage")
        write_ledger(ledger_file, ledger)
        raise BridgeError("uncertain", attempt["error"], 6)

    text = raw.get("text")
    if not isinstance(text, str) or not text.strip():
        attempt["status"] = "uncertain"
        attempt["error"] = "Letta returned no assistant text"
        attempt["usage"] = raw.get("usage")
        write_ledger(ledger_file, ledger)
        raise BridgeError("uncertain", attempt["error"], 6)

    usage = raw.get("usage") if isinstance(raw.get("usage"), dict) else None
    result = {
        "status": "succeeded",
        "task_id": ctx["PAPERCLIP_TASK_ID"],
        "run_id": ctx["PAPERCLIP_RUN_ID"],
        "worker": slug,
        "paperclip_agent_id": ctx["PAPERCLIP_AGENT_ID"],
        "letta_id": worker["letta_id"],
        "task_type": kind,
        "input_sha256": input_hash,
        "output_sha256": sha256_text(text),
        "text": text,
        "usage": usage,
        "usage_known": usage is not None,
        "provider_spend_cap_enforced": False,
        "provider_monetary_cost": "unknown",
        "paperclip_issue_marked_complete": False,
    }
    attempt.update({
        "status": "succeeded",
        "output_sha256": result["output_sha256"],
        "usage": usage,
    })
    write_ledger(ledger_file, ledger)
    return result


def default_fetch_issue(ctx: dict[str, str]) -> dict[str, Any]:
    import urllib.request

    url = ctx["PAPERCLIP_API_URL"].rstrip("/") + "/api/issues/" + ctx["PAPERCLIP_TASK_ID"]
    req = urllib.request.Request(url, headers={"Authorization": "Bearer " + ctx["PAPERCLIP_API_KEY"]})
    with urllib.request.urlopen(req, timeout=20) as response:
        payload = json.loads(response.read().decode("utf-8"))
    if not isinstance(payload, dict):
        raise BridgeError("blocked", "Paperclip issue payload was not an object", 3)
    return payload


def default_invoke_letta(agent_id: str, prompt: str) -> dict[str, Any]:
    import subprocess

    binary = os.environ.get("LETTA_BIN", "letta")
    cmd = [
        binary, "--backend", "local", "--agent", agent_id, "--new", "-p", prompt,
        "--output-format", "json", "--reflection-trigger", "off",
        "--no-bundled-skills", "--no-mods", "--no-system-info-reminder",
    ]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=180, env={**os.environ, "CI": "1", "NO_COLOR": "1"})
    except subprocess.TimeoutExpired as exc:
        raise TimeoutError("Letta call timed out") from exc
    parsed: Any = None
    try:
        parsed = json.loads(proc.stdout or "")
    except json.JSONDecodeError:
        parsed = None
    text = ""
    usage = None
    if isinstance(parsed, dict):
        if isinstance(parsed.get("result"), str):
            text = parsed["result"]
        usage = parsed.get("usage") if isinstance(parsed.get("usage"), dict) else None
        uncertain = parsed.get("subtype") != "success" or parsed.get("is_error") is True or proc.returncode != 0
    else:
        uncertain = True
    return {
        "text": text,
        "usage": usage,
        "returncode": proc.returncode,
        "uncertain": uncertain,
        "error": (proc.stderr or "")[-500:],
    }


def specific_task_id(context: Any) -> str:
    """Use only the wake context's own task id. Never scan or guess a task."""
    if not isinstance(context, dict):
        raise BridgeError("blocked", "Paperclip wake context was missing", 3)
    task = context.get("taskId")
    issue = context.get("issueId")
    task_id = task.strip() if isinstance(task, str) else ""
    issue_id = issue.strip() if isinstance(issue, str) else ""
    if task_id and issue_id and task_id != issue_id:
        raise BridgeError("blocked", "context.taskId and context.issueId disagree", 2)
    chosen = task_id or issue_id
    if not chosen:
        raise BridgeError("blocked", "Paperclip wake context has no specific task id", 3)
    return chosen


def worker_for_paperclip_agent(roster: dict[str, Any], agent_id: str, slug_hint: str | None) -> tuple[str, dict[str, Any]]:
    matches = [
        (slug, worker)
        for slug, worker in roster.get("workers", {}).items()
        if isinstance(worker, dict) and worker.get("paperclip_agent_id") == agent_id
    ]
    if len(matches) != 1:
        raise BridgeError("blocked", "Paperclip agent id is not pinned to exactly one worker", 2)
    slug, worker = matches[0]
    if slug_hint and slug_hint != slug:
        raise BridgeError("blocked", "Wake URL worker does not match the Paperclip agent id", 2)
    return slug, worker


def env_from_http_wake(body: Any, roster: dict[str, Any], slug_hint: str | None, environ: dict[str, str]) -> dict[str, str]:
    if not isinstance(body, dict):
        raise BridgeError("blocked", "Paperclip HTTP body was not an object", 3)
    context = body.get("context")
    task_id = specific_task_id(context)
    agent_id = body.get("agentId")
    run_id = body.get("runId")
    if not isinstance(agent_id, str) or not agent_id.strip():
        raise BridgeError("blocked", "Paperclip HTTP body has no agentId", 2)
    if not isinstance(run_id, str) or not run_id.strip():
        raise BridgeError("blocked", "Paperclip HTTP body has no runId", 2)
    company_id = environ.get("MYHYV_PAPERCLIP_COMPANY_ID", "").strip()
    api_url = environ.get("PAPERCLIP_API_URL", "").strip()
    api_key = environ.get("PAPERCLIP_API_KEY", "").strip()
    if not company_id or not api_url or not api_key:
        raise BridgeError("blocked", "Bridge is missing its pinned Paperclip company or API settings", 2)
    # A company id inside the POST cannot choose the company.
    slug, _worker = worker_for_paperclip_agent(roster, agent_id.strip(), slug_hint)
    return {
        "PAPERCLIP_AGENT_ID": agent_id.strip(),
        "PAPERCLIP_COMPANY_ID": company_id,
        "PAPERCLIP_API_URL": api_url,
        "PAPERCLIP_API_KEY": api_key,
        "PAPERCLIP_RUN_ID": run_id.strip(),
        "PAPERCLIP_TASK_ID": task_id,
        "PAPERCLIP_WORKER_SLUG": slug,
    }


def make_handler(roster: dict[str, Any], environ: dict[str, str], fetch_issue, invoke_letta, ledger_file: Path):
    from http.server import BaseHTTPRequestHandler

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, fmt: str, *args: Any) -> None:
            return

        def do_POST(self) -> None:  # noqa: N802
            parts = [part for part in self.path.split("?")[0].split("/") if part]
            slug_hint = parts[1] if len(parts) == 2 and parts[0] == "wake" else None
            if not parts or parts[0] != "wake" or len(parts) > 2:
                self._send(404, {"status": "blocked", "error": "Unknown path"})
                return
            length = int(self.headers.get("content-length", "0") or "0")
            raw = self.rfile.read(length) if length else b""
            try:
                body = json.loads(raw.decode("utf-8"))
                env = env_from_http_wake(body, roster, slug_hint, environ)
                result = execute(
                    env,
                    roster=roster,
                    fetch_issue=fetch_issue,
                    invoke_letta=invoke_letta,
                    ledger_file=ledger_file,
                )
            except BridgeError as exc:
                self._send(422, {
                    "status": exc.status,
                    "error": str(exc),
                    "paperclip_issue_marked_complete": False,
                    "provider_spend_cap_enforced": False,
                })
                return
            except Exception as exc:
                self._send(500, {
                    "status": "provider_error",
                    "error": type(exc).__name__,
                    "paperclip_issue_marked_complete": False,
                })
                return
            self._send(200, result)

        def _send(self, status: int, payload: dict[str, Any]) -> None:
            data = json.dumps(payload).encode("utf-8")
            self.send_response(status)
            self.send_header("content-type", "application/json")
            self.send_header("content-length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

    return Handler


def serve(environ: dict[str, str] | None = None) -> None:
    from http.server import ThreadingHTTPServer

    environ = dict(os.environ if environ is None else environ)
    host = "127.0.0.1"
    port = int(environ.get("MYHYV_BRIDGE_PORT", "8765"))
    roster = load_roster()
    server = ThreadingHTTPServer((host, port), make_handler(
        roster,
        environ,
        default_fetch_issue,
        default_invoke_letta,
        ledger_path(),
    ))
    print(f"listening {host} {server.server_address[1]}", file=sys.stderr, flush=True)
    server.serve_forever()


def main() -> int:
    if "--serve" in sys.argv:
        serve()
        return 0
    try:
        result = execute(
            dict(os.environ),
            roster=load_roster(),
            fetch_issue=default_fetch_issue,
            invoke_letta=default_invoke_letta,
            ledger_file=ledger_path(),
        )
    except BridgeError as exc:
        print(json.dumps({
            "status": exc.status,
            "error": str(exc),
            "paperclip_issue_marked_complete": False,
            "provider_spend_cap_enforced": False,
        }))
        return exc.exit_code
    print(json.dumps(result))
    return 0


if __name__ == "__main__":
    sys.exit(main())
