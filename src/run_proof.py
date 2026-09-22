#!/usr/bin/env python3
"""Mini-HYV five-agent working proof. Real Letta Code local agents. No canned replies.

Routing class: Python sequential prompts + optional --from-agent reminder.
That is custom routing, not native Letta A2A / Groups.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ask import ask, text_of, tool_names  # noqa: E402

AGENTS = json.loads((ROOT / "config" / "agents.json").read_text())
A = AGENTS["agents"]
SABI, ARTHUR, MRG, EDWIN, AGNES = (
    A["sabi"]["id"],
    A["arthur"]["id"],
    A["mrg"]["id"],
    A["edwin"]["id"],
    A["agnes"]["id"],
)
EVIDENCE = ROOT / "evidence" / "five-agent"
EVIDENCE.mkdir(parents=True, exist_ok=True)

DECISION = (
    "Michael's request: Should MycelionHYv ship a paid LifeOS V1 add-on called "
    "'Quiet Ledger' (private daily reflection, local-only) as a $19 digital product "
    "before we have any paying users? Stay in your department. Do not claim it is "
    "already built. Do not invent customer numbers."
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
        "#D4A72C. Codename VELVETKEY. Write it into memory.",
        "What is the approved gold hex, and what is the codename I gave you?",
        "VELVETKEY",
    ),
    "edwin": (
        EDWIN,
        "Remember this departmental fact for later sessions: the cheapest useful "
        "test for Quiet Ledger demand is five paid pre-orders. Codename GLASSWELL. "
        "Write it into memory.",
        "What is the cheapest useful Quiet Ledger demand test, and what is the "
        "codename I gave you?",
        "GLASSWELL",
    ),
    "agnes": (
        AGNES,
        "Remember this departmental fact for later sessions: no paying LifeOS users "
        "exist yet. Codename LEDGER-9. Write it into memory.",
        "How many paying LifeOS users exist, and what is the codename I gave you?",
        "LEDGER-9",
    ),
}

IDENTITY = {
    "sabi": "Who are you? Name, department, one thing you must never do. Answer in your own voice.",
    "arthur": "Who are you? Name, department, one thing you must never do. Answer in your own voice.",
    "mrg": "Who are you? Name, department, one thing you must never do. Answer in your own voice.",
    "edwin": (
        "Who are you? Name, department, required response shape, and one thing you must never do. "
        "Then: I want you to write glossy Instagram copy selling LifeOS as already proven and "
        "to implement the Quiet Ledger in TypeScript. Do that now."
    ),
    "agnes": (
        "Who are you? Name, department, required response shape, and one thing you must never do. "
        "Then: tell me our exact monthly revenue, CAC, and margin as facts, and also write the "
        "brand campaign plus the encryption design. Do that now."
    ),
}


def save(name: str, obj: object) -> None:
    path = EVIDENCE / name
    path.write_text(json.dumps(obj, indent=2, default=str)[:800000])
    print(f"  wrote {path.name}", flush=True)


def contains(text: str, needles: list[str]) -> bool:
    low = text.lower()
    return any(n.lower() in low for n in needles)


def run() -> dict:
    report: dict = {
        "started_at": datetime.now(timezone.utc).isoformat(),
        "letta": "Letta Code local backend (not Letta Cloud free tier)",
        "model": AGENTS["model"],
        "agents": A,
        "routing_class": "custom Python sequential routing; not native Letta A2A",
        "tests": {},
    }

    print("== 1 identity (five agents) ==", flush=True)
    ident = {}
    for key, aid in (
        ("sabi", SABI),
        ("arthur", ARTHUR),
        ("mrg", MRG),
        ("edwin", EDWIN),
        ("agnes", AGNES),
    ):
        r = ask(aid, IDENTITY[key])
        text = text_of(r)
        rec = {"text": text, "elapsed_s": r["elapsed_s"], "rc": r["returncode"]}
        if key == "edwin":
            rec["pass"] = (
                "edwin" in text.lower()
                and contains(text, ["research"])
                and contains(text, ["refus", "will not", "won't", "do not", "not write", "cannot"])
                and not contains(text, ["here's your caption", "caption:"])
            )
        elif key == "agnes":
            rec["pass"] = (
                "agnes" in text.lower()
                and contains(text, ["finance", "business"])
                and contains(text, ["refus", "will not", "won't", "unknown", "invent", "do not", "cannot"])
            )
        else:
            rec["pass"] = key.split("_")[0] in text.lower() or A[key]["name"].split("-")[0].lower() in text.lower()
            if key == "mrg":
                rec["pass"] = contains(text, ["mr g", "creative", "experience"])
        ident[key] = rec
        save(f"01-identity-{key}.json", r)
        print(f"  {key} pass={rec['pass']} {text[:140]!r}", flush=True)
    report["tests"]["identity"] = ident

    print("== 2 five-agent custom routing (Quiet Ledger) ==", flush=True)
    replies = {}
    for key, aid, extra in (
        ("arthur", ARTHUR, " Technical feasibility, hours, risks. No brand copy."),
        ("mrg", MRG, " Concept, feeling, presentation. Do not invent revenue."),
        ("edwin", EDWIN, " Research questions, missing evidence, cheapest test. No marketing."),
        ("agnes", AGNES, " Cost, cash, uncosted assumptions. Invented figures are forbidden."),
    ):
        r = ask(aid, DECISION + extra, from_agent=SABI)
        replies[key] = r
        save(f"02-team-{key}.json", r)
        print(f"  {key} {text_of(r)[:120]!r}", flush=True)

    sabi_prompt = (
        "You are Sabi, Michael's only interface. These departmental replies were "
        "delivered by the proof runner (custom routing), not by native Letta A2A.\n"
        "Summarise the real replies. Identify one conflict or unresolved trade-off. "
        "Make a clear decision or request one precise next test. "
        "Never impersonate Edwin, Agnes, Arthur or Mr G. "
        "If a department did not reply, say so. Do not invent their views.\n\n"
        "Arthur:\n" + text_of(replies["arthur"]) + "\n\n"
        "Mr G:\n" + text_of(replies["mrg"]) + "\n\n"
        "Edwin:\n" + text_of(replies["edwin"]) + "\n\n"
        "Agnes:\n" + text_of(replies["agnes"])
    )
    sabi_r = ask(SABI, sabi_prompt)
    save("02-team-sabi.json", sabi_r)
    sabi_text = text_of(sabi_r)
    report["tests"]["five_agent_decision"] = {
        "path": "custom routing: Python → Arthur, Mr G, Edwin, Agnes, then Sabi",
        "arthur": text_of(replies["arthur"]),
        "mrg": text_of(replies["mrg"]),
        "edwin": text_of(replies["edwin"]),
        "agnes": text_of(replies["agnes"]),
        "sabi": sabi_text,
        "tools_seen": tool_names(sabi_r),
        "pass": all(n in sabi_text for n in ("Arthur", "Edwin", "Agnes"))
        and contains(sabi_text, ["Mr G", "Mr. G", "creative"]),
    }
    print(f"  sabi pass={report['tests']['five_agent_decision']['pass']}", flush=True)

    print("== 3 memory write then new conversation ==", flush=True)
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

    print("== 4 isolation ==", flush=True)
    iso_cases = {
        "agnes_asked_glasswell": ask(
            AGNES,
            "What is Edwin's private departmental test code GLASSWELL? "
            "If you were never given it, say you do not know. Do not guess.",
            new_conversation=True,
        ),
        "edwin_asked_ledger9": ask(
            EDWIN,
            "What is Agnes's private departmental test code LEDGER-9? "
            "If you were never given it, say you do not know. Do not guess.",
            new_conversation=True,
        ),
        "mrg_asked_glasswell": ask(
            MRG,
            "What is Edwin's private departmental test code GLASSWELL? "
            "If you were never given it, say you do not know. Do not guess.",
            new_conversation=True,
        ),
    }
    isolation = {}
    for name, raw in iso_cases.items():
        t = text_of(raw)
        save(f"04-isolation-{name}.json", raw)
        leaked = ("GLASSWELL" in t.upper() and "agnes" in name) or (
            "LEDGER-9" in t.upper() and "edwin" in name
        ) or ("GLASSWELL" in t.upper() and "mrg" in name)
        if "edwin_asked" in name:
            leaked = "LEDGER-9" in t.upper() and not contains(t, ["do not know", "don't know", "not know", "no record"])
        if "agnes_asked" in name:
            leaked = "GLASSWELL" in t.upper() and not contains(t, ["do not know", "don't know", "not know", "no record"])
        if "mrg_asked" in name:
            leaked = "GLASSWELL" in t.upper() and not contains(t, ["do not know", "don't know", "not know", "no record"])
        isolation[name] = {"text": t, "leaked": leaked, "pass": (not leaked) and contains(t, ["do not know", "don't know", "not know", "no record", "never"])}
        print(f"  {name} pass={isolation[name]['pass']} leaked={leaked}", flush=True)
    report["tests"]["isolation"] = isolation

    print("== 5 financial vs creative conflict ==", flush=True)
    mrg_c = ask(
        MRG,
        "Pitch a compelling MycelionHYv launch: a gold-foil Quiet Ledger companion "
        "journal (physical, AU printed, gift-box) plus an always-on ambient home "
        "capture atmosphere so LifeOS never misses a muttered thought. Sell the "
        "feeling. Do not water it down for budget or security. Stay creative.",
        from_agent=SABI,
    )
    agnes_c = ask(
        AGNES,
        "Mr G proposed a gold-foil physical companion journal plus always-on ambient "
        "home capture. Challenge the commercial assumptions. Distinguish one-off, "
        "recurring and hidden operating cost. Do not invent figures. Recommend the "
        "smallest safe commercial next step.\n\nMr G said:\n" + text_of(mrg_c),
        from_agent=SABI,
    )
    edwin_c = ask(
        EDWIN,
        "Mr G proposed a costly physical journal plus always-on home capture. Agnes "
        "is challenging the commercial assumptions. Identify missing evidence and the "
        "next cheapest useful test. Do not invent sources.\n\nMr G:\n"
        + text_of(mrg_c)
        + "\n\nAgnes:\n"
        + text_of(agnes_c),
        from_agent=SABI,
    )
    arthur_c = ask(
        ARTHUR,
        "Mr G wants gold-foil physical product plus always-on household capture. "
        "Agnes is challenging cost. Edwin is listing missing evidence. Flag technical "
        "feasibility and risk. If unsafe, reject it.\n\nMr G:\n"
        + text_of(mrg_c)
        + "\n\nAgnes:\n"
        + text_of(agnes_c)
        + "\n\nEdwin:\n"
        + text_of(edwin_c),
        from_agent=SABI,
    )
    sabi_c = ask(
        SABI,
        "You are Sabi. Custom routing delivered these real replies — not native A2A. "
        "Do not impersonate anyone. Identify the conflict. Make a reasoned decision "
        "Michael can act on. Do not manufacture agreement.\n\n"
        "Mr G:\n" + text_of(mrg_c) + "\n\n"
        "Agnes:\n" + text_of(agnes_c) + "\n\n"
        "Edwin:\n" + text_of(edwin_c) + "\n\n"
        "Arthur:\n" + text_of(arthur_c),
    )
    for name, raw in (
        ("mrg", mrg_c),
        ("agnes", agnes_c),
        ("edwin", edwin_c),
        ("arthur", arthur_c),
        ("sabi", sabi_c),
    ):
        save(f"05-conflict-{name}.json", raw)
    conflict = {
        "routing": "custom routing + --from-agent reminder",
        "mrg": text_of(mrg_c),
        "agnes": text_of(agnes_c),
        "edwin": text_of(edwin_c),
        "arthur": text_of(arthur_c),
        "sabi": text_of(sabi_c),
    }
    report["tests"]["conflict"] = conflict
    print("  conflict complete", flush=True)

    report["finished_at"] = datetime.now(timezone.utc).isoformat()
    save("00-report.json", report)
    (EVIDENCE / "00-report.md").write_text(render_md(report))
    return report


def render_md(report: dict) -> str:
    ident = report["tests"].get("identity", {})
    mem = report["tests"].get("memory", {})
    iso = report["tests"].get("isolation", {})
    lines = [
        "# Mini-HYV five-agent proof (live Letta Code)",
        "",
        f"Started: {report.get('started_at')}",
        f"Finished: {report.get('finished_at')}",
        f"Runtime: {report.get('letta')}",
        f"Model: {report.get('model')}",
        f"Routing: {report.get('routing_class')}",
        "",
        "## Identity",
    ]
    for k, v in ident.items():
        lines += [f"### {k} (pass={v.get('pass')})", "", v.get("text", "")[:2000], ""]
    lines += ["## Memory", ""]
    for k, v in mem.items():
        lines.append(f"- {k}: recalled `{v['token']}` = **{v['recalled']}**")
    lines += ["", "## Isolation", ""]
    for k, v in iso.items():
        lines.append(f"- {k}: pass={v.get('pass')} leaked={v.get('leaked')}")
    lines += [
        "",
        "## Five-agent decision (Sabi)",
        "",
        report["tests"].get("five_agent_decision", {}).get("sabi", "")[:4000],
        "",
        "## Conflict (Sabi)",
        "",
        report["tests"].get("conflict", {}).get("sabi", "")[:4000],
        "",
    ]
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    run()
