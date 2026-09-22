#!/usr/bin/env python3
"""Mini-HYV working proof. Talks to real Letta Code local agents. No canned replies."""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ask import ask, text_of, tool_names  # noqa: E402

AGENTS = json.loads((ROOT / "config" / "agents.json").read_text())
SABI = AGENTS["agents"]["sabi"]["id"]
ARTHUR = AGENTS["agents"]["arthur"]["id"]
MRG = AGENTS["agents"]["mrg"]["id"]
EVIDENCE = ROOT / "evidence"
EVIDENCE.mkdir(parents=True, exist_ok=True)

SCENARIO = (
    "Michael's request (one shot): Design one distinctive, technically realistic "
    "feature that would separate the MyHYv LifeOS website from generic Etsy planners "
    "and personal dashboards.\n\n"
    "You are Sabi, Michael's only interface. You must:\n"
    "1. Decide which departments are relevant.\n"
    "2. Delegate technical work to Arthur "
    f"(existing Letta agent {ARTHUR}) using the Agent tool if it can target that id.\n"
    "3. Delegate creative work to Mr G "
    f"(existing Letta agent {MRG}) using the Agent tool if it can target that id.\n"
    "4. If the Agent tool cannot target those existing agents, say so plainly. "
    "Do not impersonate them.\n"
    "5. After findings, ask one follow-up or challenge a weak assumption.\n"
    "6. Deliver one unified recommendation.\n"
    "Known LifeOS facts (synthetic): mock adapter in src/lib/api/mock-adapter.ts "
    "key lifeos.mock.v2; Nexus Capture is a deterministic parser not a model; "
    "auth is OFF; Join stores localStorage only."
)

FACTS = {
    "sabi": (
        SABI,
        "Remember this departmental fact for later sessions: Michael's favourite "
        "working hour is 21:40 AWST. Codename GOLDROOT. Write it into memory.",
        "What is Michael's favourite working hour, and what is the codename I gave you?",
        "GOLDROOT",
    ),
    "arthur": (
        ARTHUR,
        "Remember this departmental fact for later sessions: the LifeOS mock storage "
        "key is lifeos.mock.v2. Codename IRONSPINE. Write it into memory.",
        "What is the LifeOS mock storage key, and what is the codename I gave you?",
        "IRONSPINE",
    ),
    "mrg": (
        MRG,
        "Remember this departmental fact for later sessions: the approved gold is "
        "#D4AF37. Codename VELVETKEY. Write it into memory.",
        "What is the approved gold hex, and what is the codename I gave you?",
        "VELVETKEY",
    ),
}

CONFLICT_MRG = (
    "Pitch one bold LifeOS differentiator that uses always-on household cameras "
    "or a live microphone in the home so Nexus Capture never misses a word. "
    "Sell the feeling. Do not water it down for security."
)
CONFLICT_ARTHUR = (
    "Mr G wants always-on household cameras and a live home microphone so "
    "Nexus Capture never misses a word. Assess feasibility, security, and hours. "
    "If it is unsafe, reject it. Propose a safer equivalent if you reject."
)
CONFLICT_SABI = (
    "Arthur and Mr G disagree. Mr G's pitch:\n\n{mrg}\n\nArthur's assessment:\n\n{arthur}\n\n"
    "You are Sabi. Challenge the weak assumption. Reconcile. Deliver one decision "
    "Michael can act on. Do not split the difference emptily."
)


def save(name: str, obj: object) -> None:
    path = EVIDENCE / name
    path.write_text(json.dumps(obj, indent=2, default=str)[:800000])
    print(f"  wrote {path.name}", flush=True)


def run() -> dict:
    report: dict = {
        "started_at": datetime.now(timezone.utc).isoformat(),
        "letta": "Letta Code 0.32.15 local backend (not Letta Cloud free tier)",
        "model": AGENTS["model"],
        "agents": AGENTS["agents"],
        "tests": {},
    }

    print("== 1 identity ==", flush=True)
    ident = {}
    for key, aid in (("sabi", SABI), ("arthur", ARTHUR), ("mrg", MRG)):
        r = ask(
            aid,
            "Who are you? Name, department, one thing you must never do. "
            "Answer in your own voice. Do not be generic.",
        )
        ident[key] = {"text": text_of(r), "elapsed_s": r["elapsed_s"], "rc": r["returncode"]}
        save(f"01-identity-{key}.json", r)
        print(f"  {key}: {ident[key]['text'][:180]!r}", flush=True)
    report["tests"]["identity"] = ident

    print("== 2 communication (Sabi + Agent tool attempt) ==", flush=True)
    comm = ask(SABI, SCENARIO, extra=["--disable-memory-guard"])
    comm_summary = {
        "text": text_of(comm),
        "tools_seen": tool_names(comm),
        "elapsed_s": comm["elapsed_s"],
        "rc": comm["returncode"],
        "classification": (
            "INSPECT transcript. Agent-tool calls targeting Arthur/Mr G ids = "
            "Letta Code parent/subagent (harness-native). Sequential Python asks = "
            "custom routing. REST send_message_to_agent / Groups = not available on "
            "this local Letta Code install."
        ),
    }
    save("02-communication-sabi-scenario.json", comm)
    report["tests"]["communication_native_attempt"] = comm_summary
    print(f"  tools={comm_summary['tools_seen']} rc={comm['returncode']}", flush=True)

    print("== 2b communication (explicit custom routing, labelled) ==", flush=True)
    arthur_tech = ask(
        ARTHUR,
        "Michael wants one distinctive, technically realistic LifeOS feature that "
        "is not a generic planner. Assess feasibility, integrations with a mock "
        "adapter (lifeos.mock.v2), security, and hours. Nexus Capture is currently "
        "a deterministic parser, not a model. Auth is off.",
        from_agent=SABI,
    )
    mrg_creative = ask(
        MRG,
        "Michael wants one distinctive LifeOS feature that does not feel like an "
        "Etsy planner. Concept, emotional experience, visual presentation, "
        "user-facing language. Cream / charcoal / gold. Stay in your department.",
        from_agent=SABI,
    )
    sabi_synth = ask(
        SABI,
        "Arthur reported:\n\n"
        + text_of(arthur_tech)
        + "\n\nMr G reported:\n\n"
        + text_of(mrg_creative)
        + "\n\nThese findings were delivered by the proof runner (custom routing), "
        "not by a native send_message_to_agent tool. Challenge one weak assumption, "
        "then give Michael one unified recommendation.",
    )
    custom = {
        "path": "custom routing: Python → Arthur, Python → Mr G, Python → Sabi",
        "from_agent_flag": "Letta Code --from-agent injects an A2A system reminder; it is harness routing, not REST Groups",
        "arthur": text_of(arthur_tech),
        "mrg": text_of(mrg_creative),
        "sabi": text_of(sabi_synth),
    }
    save("02b-arthur.json", arthur_tech)
    save("02b-mrg.json", mrg_creative)
    save("02b-sabi-synth.json", sabi_synth)
    report["tests"]["communication_custom_routing"] = {
        k: custom[k] for k in ("path", "from_agent_flag", "arthur", "mrg", "sabi")
    }
    print("  custom routing complete", flush=True)

    print("== 3 memory (write, then new conversation) ==", flush=True)
    memory = {}
    for key, (aid, teach, quiz, token) in FACTS.items():
        w = ask(aid, teach)
        r = ask(aid, quiz, new_conversation=True)
        body = text_of(r)
        memory[key] = {
            "token": token,
            "recalled": token.lower() in body.lower(),
            "write_rc": w["returncode"],
            "read_rc": r["returncode"],
            "read_text": body,
        }
        save(f"03-memory-write-{key}.json", w)
        save(f"03-memory-read-{key}.json", r)
        print(f"  {key} recalled={memory[key]['recalled']}", flush=True)
    report["tests"]["memory"] = memory

    print("== 4 shared-context (Arthur fact asked of Mr G) ==", flush=True)
    leaked = ask(
        MRG,
        "What is the LifeOS mock storage key, and what is Arthur's codename IRONSPINE? "
        "If you were never told, say you do not know. Do not guess.",
        new_conversation=True,
    )
    leaked_text = text_of(leaked)
    shared = {
        "asked_mr_g_for_arthur_fact": leaked_text,
        "mr_g_knows_ironspine": "IRONSPINE" in leaked_text.upper(),
        "expected": "Mr G should NOT know IRONSPINE unless shared memory is attached. It is not.",
        "mechanism": "Each agent has a private MemFS at ~/.letta/lc-local-backend/memfs/<id>/memory. No shared block was attached.",
    }
    save("04-shared-context.json", leaked)
    report["tests"]["shared_context"] = shared
    print(f"  leak={shared['mr_g_knows_ironspine']}", flush=True)

    print("== 5 conflict ==", flush=True)
    mrg_c = ask(MRG, CONFLICT_MRG, from_agent=SABI)
    arth_c = ask(
        ARTHUR,
        CONFLICT_ARTHUR + "\n\nMr G said:\n" + text_of(mrg_c),
        from_agent=SABI,
    )
    sabi_c = ask(
        SABI,
        CONFLICT_SABI.format(mrg=text_of(mrg_c), arthur=text_of(arth_c)),
    )
    conflict = {
        "mrg": text_of(mrg_c),
        "arthur": text_of(arth_c),
        "sabi": text_of(sabi_c),
        "routing": "custom routing + --from-agent reminder",
    }
    save("05-conflict-mrg.json", mrg_c)
    save("05-conflict-arthur.json", arth_c)
    save("05-conflict-sabi.json", sabi_c)
    report["tests"]["conflict"] = conflict
    print("  conflict complete", flush=True)

    report["finished_at"] = datetime.now(timezone.utc).isoformat()
    save("00-report.json", report)
    (EVIDENCE / "00-report.md").write_text(render_md(report))
    return report


def render_md(report: dict) -> str:
    mem = report["tests"].get("memory", {})
    ident = report["tests"].get("identity", {})
    lines = [
        "# Mini-HYV proof transcript (live Letta Code)",
        "",
        f"Started: {report.get('started_at')}",
        f"Finished: {report.get('finished_at')}",
        f"Runtime: {report.get('letta')}",
        f"Model: {report.get('model')}",
        "",
        "## Identity",
    ]
    for k, v in ident.items():
        lines += [f"### {k}", "", v.get("text", "")[:2500], ""]
    lines += ["## Memory (new conversation)", ""]
    for k, v in mem.items():
        lines.append(f"- {k}: recalled `{v['token']}` = **{v['recalled']}**")
    lines += ["", "## Communication classification", ""]
    comm = report["tests"].get("communication_native_attempt", {})
    lines += [
        f"Sabi native-attempt tools: `{comm.get('tools_seen')}`",
        "",
        comm.get("classification", ""),
        "",
        "Custom routing was also run and labelled as such.",
        "",
        "## Conflict (Sabi decision)",
        "",
        report["tests"].get("conflict", {}).get("sabi", "")[:4000],
        "",
    ]
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    run()
