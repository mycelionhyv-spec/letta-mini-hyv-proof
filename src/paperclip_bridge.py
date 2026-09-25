#!/usr/bin/env python3
"""Fail-closed Paperclip HTTP bridge to one pinned Letta agent.

This file does not start Paperclip and does not mark a run complete unless the
Letta call returns a definite assistant result. Missing, mismatched, duplicate,
budget, timeout and unresolved-ID cases exit non-zero before any model call.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import sys
import tempfile
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[1]
ROSTER_PATH = ROOT / "config" / "paperclip-roster.json"
TERMINAL_STATUSES = {"done", "completed", "cancelled", "canceled", "closed"}
MAX_WAKE_BYTES = 65536
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
    configured = os.environ.get("MYHYV_BRIDGE_ROSTER")
    raw = json.loads((path or (Path(configured) if configured else ROSTER_PATH)).read_text())
    if "workers" not in raw or "excluded" not in raw:
        raise BridgeError("blocked", "Roster is missing workers or excluded", 2)
    return raw


def ledger_path(environ: dict[str, str] | None = None) -> Path:
    configured = (os.environ if environ is None else environ).get("MYHYV_BRIDGE_LEDGER")
    if configured:
        return Path(configured)
    return Path.home() / ".local" / "state" / "myhyv" / "bridge" / "ledger.json"


def read_ledger(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"runs": []}
    data = json.loads(path.read_text())
    if not isinstance(data, dict) or not isinstance(data.get("runs"), list):
        raise BridgeError("blocked", "Run ledger is unreadable; refusing to continue", 2)
    return data


def write_ledger(path: Path, data: dict[str, Any]) -> None:
    """Persist private JSON before returning; never expose a partial file."""
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    fd, name = tempfile.mkstemp(prefix=".bridge-", suffix=".tmp", dir=path.parent)
    tmp = Path(name)
    try:
        with os.fdopen(fd, "w") as stream:
            json.dump(data, stream, indent=2)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        tmp.replace(path)
        directory = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    finally:
        tmp.unlink(missing_ok=True)


@contextmanager
def invocation_lock(path: Path):
    """One invocation at a time across threads and processes on a POSIX host."""
    import fcntl

    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    fd = os.open(str(path) + ".lock", os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    try:
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise BridgeError("blocked", "Another bridge invocation is active", 8) from exc
        yield
    finally:
        os.close(fd)


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
    if status not in {"todo", "in_progress"}:
        raise BridgeError("blocked", "Task is not in a runnable trial state", 2)
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
    agent_id = worker["letta_id"]
    if any(item.get("id") == agent_id for item in roster.get("excluded", {}).values() if isinstance(item, dict)):
        raise BridgeError("blocked", "Worker maps to an excluded Letta identity", 2)
    if sum(item.get("letta_id") == agent_id for item in roster["workers"].values() if isinstance(item, dict)) != 1:
        raise BridgeError("blocked", "Letta identity is shared by more than one worker", 2)
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
    with invocation_lock(ledger_file):
        return _execute_locked(
            env, roster=roster, fetch_issue=fetch_issue,
            invoke_letta=invoke_letta, ledger_file=ledger_file,
        )


def _execute_locked(
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
    worker_for_paperclip_agent(roster, ctx["PAPERCLIP_AGENT_ID"], slug)
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
        "company_id": ctx["PAPERCLIP_COMPANY_ID"],
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
        attempt["error"] = "Letta call timed out; do not retry automatically"
        write_ledger(ledger_file, ledger)
        raise BridgeError("timeout", attempt["error"], 6) from exc
    except Exception as exc:
        attempt["status"] = "provider_error"
        attempt["error"] = "Letta invocation failed; outcome must be reviewed"
        write_ledger(ledger_file, ledger)
        raise BridgeError("provider_error", attempt["error"], 6) from exc

    if not isinstance(raw, dict):
        raw = {"uncertain": True}
    if raw.get("uncertain") or raw.get("returncode") not in (0, None):
        attempt["status"] = "uncertain"
        attempt["error"] = "Letta result was not a definite success"
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
        "company_id": ctx["PAPERCLIP_COMPANY_ID"],
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
    receipt_id = sha256_text(json.dumps([
        ctx["PAPERCLIP_COMPANY_ID"], ctx["PAPERCLIP_TASK_ID"], ctx["PAPERCLIP_RUN_ID"],
    ]))
    receipt = ledger_file.parent / "receipts" / (receipt_id + ".json")
    result["receipt_path"] = str(receipt)
    write_ledger(receipt, result)
    attempt.update({
        "status": "succeeded",
        "output_sha256": result["output_sha256"],
        "usage": usage,
        "receipt_path": str(receipt),
    })
    write_ledger(ledger_file, ledger)
    return result


def default_fetch_issue(ctx: dict[str, str]) -> dict[str, Any]:
    import urllib.request
    from urllib.parse import quote

    url = ctx["PAPERCLIP_API_URL"].rstrip("/") + "/api/issues/" + quote(ctx["PAPERCLIP_TASK_ID"], safe="")
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
        "--no-skills", "--no-mods", "--no-system-info-reminder",
        "--tools", "", "--permission-mode", "strict",
    ]
    # The provider/store settings remain available; bridge authority does not.
    child_env = {key: value for key, value in os.environ.items()
                 if not key.startswith(("PAPERCLIP_", "MYHYV_")) and key != "BRIDGE_TOKEN"}
    child_env.update({"CI": "1", "NO_COLOR": "1"})
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=180, env=child_env)
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
        "error": "Letta runtime did not return a definite success" if uncertain else None,
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
        def setup(self) -> None:
            super().setup()
            self.connection.settimeout(10)

        def log_message(self, fmt: str, *args: Any) -> None:
            return

        def do_POST(self) -> None:  # noqa: N802
            parts = [part for part in self.path.split("?")[0].split("/") if part]
            slug_hint = parts[1] if len(parts) == 2 and parts[0] == "wake" else None
            if not parts or parts[0] != "wake" or len(parts) > 2:
                self._send(404, {"status": "blocked", "error": "Unknown path"})
                return
            expected = environ.get("MYHYV_BRIDGE_WEBHOOK_TOKEN", "").strip()
            provided = self.headers.get("X-MyHYv-Bridge-Token", "").strip()
            if not expected:
                self._send(503, {"status": "blocked", "error": "Bridge authentication is not configured"})
                return
            try:
                authorized = (len(self.headers.get_all("X-MyHYv-Bridge-Token", [])) == 1
                              and bool(provided) and hmac.compare_digest(provided, expected))
            except TypeError:
                authorized = False
            if not authorized:
                self._send(401, {"status": "blocked", "error": "Unauthorized"})
                return
            try:
                if self.headers.get("transfer-encoding") or len(self.headers.get_all("content-length", [])) != 1:
                    self._send(400, {"status": "blocked", "error": "A single Content-Length is required"})
                    return
                try:
                    length = int(self.headers["content-length"])
                except ValueError:
                    length = -1
                if length <= 0 or length > MAX_WAKE_BYTES:
                    self._send(413 if length > MAX_WAKE_BYTES else 400, {"status": "blocked", "error": "Invalid body length"})
                    return
                raw = self.rfile.read(length)
                if len(raw) != length:
                    raise ValueError("Incomplete body")
                body = json.loads(raw.decode("utf-8"))
                env = env_from_http_wake(body, roster, slug_hint, environ)
                result = execute(
                    env,
                    roster=roster,
                    fetch_issue=fetch_issue,
                    invoke_letta=invoke_letta,
                    ledger_file=ledger_file,
                )
            except (ValueError, UnicodeError):
                self._send(400, {"status": "blocked", "error": "Invalid JSON wake body"})
                return
            except TimeoutError:
                self._send(408, {"status": "blocked", "error": "Wake body timed out"})
                return
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
    if not environ.get("MYHYV_BRIDGE_WEBHOOK_TOKEN", "").strip():
        raise RuntimeError("MYHYV_BRIDGE_WEBHOOK_TOKEN is required; refusing to start unauthenticated")
    roster = load_roster(Path(environ["MYHYV_BRIDGE_ROSTER"]) if environ.get("MYHYV_BRIDGE_ROSTER") else None)
    server = ThreadingHTTPServer((host, port), make_handler(
        roster,
        environ,
        default_fetch_issue,
        default_invoke_letta,
        ledger_path(environ),
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
