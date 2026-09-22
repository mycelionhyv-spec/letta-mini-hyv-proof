"""Controlled, receipt-backed orchestration for the Mini-HYV proof.

This is deliberately a custom router. It does not claim Letta native A2A.
Every departmental contribution becomes a hashed receipt before Sabi sees it.
"""

from __future__ import annotations

import hashlib
import json
import re
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Iterable

from ask import text_of

AskFn = Callable[..., dict[str, Any]]
RECEIPT_RE = re.compile(r"\[receipt:([A-Za-z0-9_-]+)\]")


class CouncilError(RuntimeError):
    """A request failed a control-plane invariant."""


class BudgetExceeded(CouncilError):
    """The request crossed its declared model-call or token budget."""


@dataclass(frozen=True)
class Limits:
    max_calls: int = 3
    max_task_chars: int = 6000
    max_total_reported_tokens: int = 90000


@dataclass(frozen=True)
class Job:
    id: str
    principal: str
    target: str
    task: str
    created_at: str

    @property
    def input_hash(self) -> str:
        return digest(self.task)


@dataclass(frozen=True)
class Receipt:
    id: str
    job_id: str
    agent: str
    input_hash: str
    output: str
    output_hash: str
    elapsed_s: float
    prompt_tokens: int | None
    completion_tokens: int | None
    total_tokens: int | None
    created_at: str

    def public(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class Decision:
    request_id: str
    answer: str
    cited_receipt_ids: tuple[str, ...]
    receipts: tuple[Receipt, ...]
    total_reported_tokens: int


def digest(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _usage(raw: dict[str, Any]) -> tuple[int | None, int | None, int | None]:
    parsed = raw.get("parsed")
    usage = parsed.get("usage", {}) if isinstance(parsed, dict) else {}
    return (
        integer_or_none(usage.get("prompt_tokens")),
        integer_or_none(usage.get("completion_tokens")),
        integer_or_none(usage.get("total_tokens")),
    )


def integer_or_none(value: Any) -> int | None:
    return value if isinstance(value, int) and value >= 0 else None


class ReceiptCouncil:
    """Routes bounded tasks and prevents unreceipted departmental claims."""

    def __init__(
        self,
        *,
        ask_fn: AskFn,
        agents: dict[str, dict[str, str]],
        evidence_dir: Path,
        limits: Limits = Limits(),
    ) -> None:
        self.ask_fn = ask_fn
        self.agents = agents
        self.evidence_dir = evidence_dir
        self.limits = limits
        self.calls = 0
        self.reported_tokens = 0

    def request(
        self,
        *,
        principal: str,
        task: str,
        departments: Iterable[str],
        request_id: str | None = None,
    ) -> Decision:
        targets = tuple(departments)
        if not task.strip():
            raise CouncilError("Task must not be empty.")
        if len(task) > self.limits.max_task_chars:
            raise CouncilError("Task exceeds max_task_chars.")
        if not targets:
            raise CouncilError("At least one department is required.")
        if len(set(targets)) != len(targets):
            raise CouncilError("Department list contains duplicates.")
        if "sabi" in targets:
            raise CouncilError("Sabi synthesises; do not route a department job to Sabi.")
        unknown = [name for name in targets if name not in self.agents]
        if unknown:
            raise CouncilError(f"Unknown department(s): {', '.join(unknown)}")
        if "sabi" not in self.agents:
            raise CouncilError("Agent config must include sabi.")

        rid = request_id or f"req-{uuid.uuid4().hex[:12]}"
        receipts = tuple(
            self._run_department(
                Job(
                    id=f"job-{uuid.uuid4().hex[:12]}",
                    principal=principal,
                    target=target,
                    task=task,
                    created_at=now(),
                )
            )
            for target in targets
        )
        decision = self._synthesise(rid, principal, task, receipts)
        self._persist(decision)
        return decision

    def _run_department(self, job: Job) -> Receipt:
        agent = self.agents[job.target]
        prompt = (
            f"You are {agent['name']} ({job.target}) in a receipt-backed council.\n"
            "Return only your own departmental analysis. Do not claim another "
            "department has spoken. State uncertainty plainly.\n\n"
            f"Task from {job.principal}:\n{job.task}"
        )
        raw = self._call(agent["id"], prompt, from_agent=self.agents["sabi"]["id"])
        output = text_of(raw).strip()
        if not output:
            raise CouncilError(f"{job.target} produced no usable output.")
        p, c, total = _usage(raw)
        return Receipt(
            id=f"rcpt-{uuid.uuid4().hex[:12]}",
            job_id=job.id,
            agent=job.target,
            input_hash=job.input_hash,
            output=output,
            output_hash=digest(output),
            elapsed_s=float(raw.get("elapsed_s") or 0),
            prompt_tokens=p,
            completion_tokens=c,
            total_tokens=total,
            created_at=now(),
        )

    def _synthesise(
        self,
        request_id: str,
        principal: str,
        task: str,
        receipts: tuple[Receipt, ...],
    ) -> Decision:
        evidence = "\n\n".join(
            f"[receipt:{r.id}] agent={r.agent} input_sha256={r.input_hash} "
            f"output_sha256={r.output_hash}\n{r.output}"
            for r in receipts
        )
        prompt = (
            "You are Sabi, coordinator. These are externally routed departmental "
            "receipts. They are not native Letta messages.\n"
            "Write one decision for Michael. Challenge the weakest assumption. "
            "Do not claim any department spoke unless you cite its exact receipt "
            "as [receipt:ID]. Do not invent findings or implementation status.\n\n"
            f"Owner request from {principal}:\n{task}\n\n"
            f"Evidence:\n{evidence}"
        )
        raw = self._call(self.agents["sabi"]["id"], prompt)
        answer = text_of(raw).strip()
        if not answer:
            raise CouncilError("Sabi produced no usable decision.")
        cited = tuple(dict.fromkeys(RECEIPT_RE.findall(answer)))
        allowed = {r.id for r in receipts}
        missing = [r.id for r in receipts if r.id not in cited]
        invalid = [rid for rid in cited if rid not in allowed]
        if missing or invalid:
            raise CouncilError(
                "Decision receipt invariant failed: "
                f"missing={missing or 'none'} invalid={invalid or 'none'}"
            )
        return Decision(
            request_id=request_id,
            answer=answer,
            cited_receipt_ids=cited,
            receipts=receipts,
            total_reported_tokens=self.reported_tokens,
        )

    def _call(self, agent_id: str, prompt: str, **kwargs: Any) -> dict[str, Any]:
        if self.calls >= self.limits.max_calls:
            raise BudgetExceeded("Maximum model-call budget reached.")
        raw = self.ask_fn(agent_id, prompt, **kwargs)
        self.calls += 1
        _, _, total = _usage(raw)
        self.reported_tokens += total or 0
        if self.reported_tokens > self.limits.max_total_reported_tokens:
            raise BudgetExceeded("Reported token budget reached.")
        if raw.get("returncode") not in (0, None):
            raise CouncilError(f"Agent call failed with rc={raw.get('returncode')}.")
        return raw

    def _persist(self, decision: Decision) -> None:
        self.evidence_dir.mkdir(parents=True, exist_ok=True)
        payload = {
            "class": "custom receipt-backed routing; not native Letta A2A",
            "request_id": decision.request_id,
            "total_reported_tokens": decision.total_reported_tokens,
            "receipts": [r.public() for r in decision.receipts],
            "decision": {
                "answer": decision.answer,
                "cited_receipt_ids": list(decision.cited_receipt_ids),
            },
        }
        path = self.evidence_dir / f"council-{decision.request_id}.json"
        path.write_text(json.dumps(payload, indent=2) + "\n")
