"""Resumable runs: state persisted after each named step; completed steps are skipped on resume."""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable

from backend.models import TraceEvent

from . import actions
from .config import limits, state_dir
from .util import atomic_write_json, read_json

Step = tuple[str, Callable[[dict], Any]]  # (name, fn(results_so_far) -> JSON-serialisable)


@dataclass
class RunResult:
    run_id: str
    status: str  # "done" | "BUDGET_HELD"
    results: dict[str, Any] = field(default_factory=dict)
    events: list[TraceEvent] = field(default_factory=list)
    held_reason: str | None = None
    recovered_torn: bool = False

    @property
    def refusal_code(self) -> str | None:
        return "BUDGET_HELD" if self.status == "BUDGET_HELD" else None


def _path(run_id: str):
    d = state_dir() / "runs"
    d.mkdir(parents=True, exist_ok=True)
    return d / f"{run_id}.json"


def load_state(run_id: str) -> tuple[dict, bool]:
    """(state, torn). A missing file is fresh; unparseable/invalid content is torn -> start clean
    (steps re-run, but the disk cache means no new network calls in replay/record)."""
    p = _path(run_id)
    if not p.exists():
        return {"steps": {}, "elapsed": 0.0}, False
    d = read_json(p)
    def _num(v):
        return isinstance(v, (int, float)) and not isinstance(v, bool)
    if (not isinstance(d, dict) or not isinstance(d.get("steps"), dict)
            or not _num(d.get("elapsed", 0.0)) or not isinstance(d.get("holds", 0), int)
            or isinstance(d.get("holds", 0), bool) or not isinstance(d.get("held", ""), str)):
        try:
            p.rename(p.with_suffix(".torn"))
        except OSError:
            pass
        return {"steps": {}, "elapsed": 0.0}, True
    d.setdefault("elapsed", 0.0)
    return d, False


def run(run_id: str, steps: list[Step], *, cost_fn: Callable[[], float] | None = None,
        clock: Callable[[], float] = time.monotonic,
        on_event: Callable[[TraceEvent], None] | None = None) -> RunResult:
    """cost_fn returns credits spent so far for this run (default: crust Ledger total).
    Limits come from config.yaml and are re-read before every step."""
    if cost_fn is None:
        from backend.crust.ledger import Ledger
        cost_fn = lambda: Ledger(run_id).total  # noqa: E731
    state, torn = load_state(run_id)
    res = RunResult(run_id=run_id, status="done", recovered_torn=torn)

    def emit(step: str, status: str, msg: str, data: dict | None = None):
        ev = TraceEvent(run_id=run_id, ts=datetime.now(timezone.utc), step=step, status=status,
                        message=msg, data=data)
        res.events.append(ev)
        if on_event:
            on_event(ev)

    if torn:
        emit("load_state", "error", "state file was torn/corrupt; restarted from step 0")
    t0 = clock()
    base_elapsed = float(state.get("elapsed", 0.0))
    state.pop("held", None)
    bypass = False
    for name, fn in steps:
        if name in state["steps"]:
            res.results[name] = state["steps"][name]
            emit(name, "cache_hit", "step already completed; skipped on resume")
            continue
        cap, tlimit = limits()  # re-read each step
        spent, elapsed = cost_fn(), base_elapsed + (clock() - t0)
        reason = None
        hold_key = f"exceed_budget:{run_id}:{state.get('holds', 0)}"
        if bypass:
            pass
        elif (spent >= cap or elapsed >= tlimit) and actions.is_approved(hold_key):
            bypass = True  # one approved overrun; consumed now
            state["holds"] = state.get("holds", 0) + 1
            actions._save(hold_key, "exceed_budget", run_id, "done")
            emit(name, "progress", f"exceed_budget approved ({hold_key}); continuing past limit once")
        elif spent >= cap:
            reason = f"credit cap reached: spent {spent:.2f} >= cap {cap:g}"
        elif elapsed >= tlimit:
            reason = f"time limit reached: {elapsed:.1f}s >= {tlimit:g}s"
        if reason:
            state["held"] = reason
            state["hold_key"] = hold_key
            if actions.get_record(hold_key) is None:
                actions._save(hold_key, "exceed_budget", run_id, "pending")
            state["elapsed"] = elapsed
            atomic_write_json(_path(run_id), state)
            res.status, res.held_reason = "BUDGET_HELD", reason
            res.results = dict(state["steps"])
            emit(name, "held_for_approval", f"BUDGET_HELD: {reason}; resumable",
                 {"refusal_code": "BUDGET_HELD", "spent": spent, "cap": cap, "approval_key": hold_key})
            return res
        emit(name, "start", "running")
        out = fn(dict(state["steps"]))
        state["steps"][name] = out
        state["elapsed"] = base_elapsed + (clock() - t0)
        atomic_write_json(_path(run_id), state)  # persist after each step
        res.results[name] = out
        emit(name, "done", "step complete", {"credits_so_far": cost_fn()})
    return res
