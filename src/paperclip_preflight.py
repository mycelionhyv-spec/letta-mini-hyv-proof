#!/usr/bin/env python3
"""Read-only host inventory. Never invokes Letta, installs, or marks agents verified."""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote

ROOT = Path(__file__).resolve().parents[1]


def inspect_host(store: Path, roster_file: Path) -> dict:
    roster = json.loads(roster_file.read_text())
    node_version = None
    if shutil.which("node"):
        result = subprocess.run(["node", "--version"], capture_output=True, text=True, timeout=10)
        match = re.fullmatch(r"v(\d+)\.(\d+)\.(\d+)", result.stdout.strip())
        if result.returncode == 0 and match:
            node_version = tuple(map(int, match.groups()))
    workers = {}
    for slug, worker in roster["workers"].items():
        agent_id = worker.get("letta_id")
        safe_id = quote(agent_id, safe="") if isinstance(agent_id, str) and agent_id else None
        workers[slug] = {
            "letta_id": agent_id,
            "agent_record_present": bool(safe_id and (store / "agents" / (safe_id + ".json")).is_file()),
            "memory_namespace_present": bool(safe_id and (store / "memfs" / safe_id / "memory").is_dir()),
            "runtime_identity_verified": False,
        }
    node_ok = bool(node_version and node_version >= (24, 11, 0))
    letta_present = bool(shutil.which(os.environ.get("LETTA_BIN", "letta")))
    paperclip_present = bool(shutil.which("paperclipai"))
    blockers = []
    if not node_ok:
        blockers.append("Node.js 24.11.0 or newer is required")
    if not letta_present:
        blockers.append("Letta executable is unavailable")
    if not paperclip_present:
        blockers.append("Paperclip executable is unavailable")
    if not store.is_dir():
        blockers.append("Configured Letta local store is unavailable")
    if not all(row["agent_record_present"] and row["memory_namespace_present"] for row in workers.values()):
        blockers.append("One or more worker records/namespaces are absent; restore or explicit rebuild is required")
    return {
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "status": "BLOCKED" if blockers else "FILES_PRESENT_RUNTIME_NOT_VERIFIED",
        "read_only": True,
        "node_version": ".".join(map(str, node_version)) if node_version else None,
        "node_supported": node_ok,
        "letta_executable_present": letta_present,
        "paperclip_executable_present": paperclip_present,
        "store_directory_present": store.is_dir(),
        "workers": workers,
        "configured_environment_names": {name: bool(os.environ.get(name)) for name in (
            "XAI_API_KEY", "LETTA_API_KEY", "PAPERCLIP_API_KEY", "MYHYV_BRIDGE_WEBHOOK_TOKEN")},
        "provider_authentication": "NOT_TESTED; providers may use a protected configuration instead of environment variables",
        "persistent_host": "NOT_VERIFIED",
        "private_network_and_auth": "NOT_VERIFIED",
        "live_dispatches": 0,
        "blockers": blockers,
        "note": "File presence does not prove identity, role, memory recovery, provider access or deployment.",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--store", type=Path, default=Path(os.environ.get(
        "LETTA_LOCAL_BACKEND_DIR", str(Path.home() / ".letta" / "lc-local-backend"))))
    parser.add_argument("--roster", type=Path, default=ROOT / "config" / "paperclip-roster.json")
    args = parser.parse_args()
    report = inspect_host(args.store.expanduser(), args.roster.expanduser())
    print(json.dumps(report, indent=2))
    return 2 if report["blockers"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
