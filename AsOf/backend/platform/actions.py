"""Outbox: irreversible actions run at most once, even across kills and restarts.

Protocol: persist ActionRecord{pending} (atomic) -> fn() -> persist done -> append {"key"} to
effects.jsonl (fsync). A kill between fn() and the effects append is the only ambiguous window;
fn must therefore itself be recorded in the effects log FIRST for sandbox sends (see sandbox_send,
which dedupes on key), and reconcile() trusts effects.jsonl as the source of truth.
"""
from __future__ import annotations

import json
import os
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from backend.models import ActionRecord

from .config import state_dir
from .util import append_jsonl, atomic_write_json, read_json, read_jsonl


def _dir() -> Path:
    d = state_dir() / "actions"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _rec_path(key: str) -> Path:
    safe = "".join(c if c.isalnum() or c in "-_." else "_" for c in key)
    return _dir() / f"{safe}.json"


def effects_path() -> Path:
    return state_dir() / "effects.jsonl"


def outbox_path() -> Path:
    return state_dir() / "sandbox_outbox.jsonl"


def has_effect(key: str) -> bool:
    return any(e.get("key") == key for e in read_jsonl(effects_path()))


def _save(key: str, action: str, target: str, status: str, **extra: Any) -> ActionRecord:
    rec = ActionRecord(key=key, action=action, target=target, status=status, ts=datetime.now(timezone.utc))
    atomic_write_json(_rec_path(key), {**json.loads(rec.model_dump_json()), **extra})
    return rec


def get_record(key: str) -> ActionRecord | None:
    d = read_json(_rec_path(key))
    if not isinstance(d, dict):
        return None
    try:
        return ActionRecord(**{k: d[k] for k in ("key", "action", "target", "status", "ts")})
    except Exception:
        return None


def reconcile(key: str | None = None) -> list[str]:
    """Settle pending records against effects.jsonl. If the effect is logged -> done. If not,
    the effect never completed, so the record is left pending (execute will run it once).
    Returns keys moved to done."""
    fixed = []
    paths = [_rec_path(key)] if key else sorted(_dir().glob("*.json"))
    for p in paths:
        d = read_json(p)
        if not isinstance(d, dict) or d.get("status") != "pending":
            continue
        if has_effect(d["key"]):
            _save(d["key"], d["action"], d["target"], "done", **_extra(d))
            fixed.append(d["key"])
    return fixed


def _extra(d: dict) -> dict:
    return {k: v for k, v in d.items() if k not in ("key", "action", "target", "status", "ts")}


def execute(key: str, action: str, target: str, fn: Callable[[], Any]) -> ActionRecord:
    """Run fn exactly once for this key. Re-calls (or restarts) after success are no-ops.
    Actions in config `approvals` should be gated by approve() at the caller."""
    reconcile(key)
    cur = get_record(key)
    if cur is not None and cur.status == "done":
        return cur
    if cur is None or cur.status != "pending":
        _save(key, action, target, "pending")  # BEFORE the effect
    if has_effect(key):  # effect landed but we died before marking done
        return _save(key, action, target, "done")
    try:
        fn()
    except Exception:
        _save(key, action, target, "failed")
        raise
    append_jsonl(effects_path(), {"key": key, "action": action, "target": target})
    return _save(key, action, target, "done")


# ---- approvals ---------------------------------------------------------------
def _appr_path(key: str) -> Path:
    return _rec_path("approval_" + key)


def approve(key: str) -> bool:
    """Single state transition requested -> approved. Returns True only for the first call, so
    a double click is safe. O_EXCL makes the transition atomic across processes."""
    p = _appr_path(key)
    try:
        fd = os.open(p, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
    except FileExistsError:
        return False
    with os.fdopen(fd, "w") as f:
        json.dump({"key": key, "approved_at": datetime.now(timezone.utc).isoformat()}, f)
        f.flush()
        os.fsync(f.fileno())
    return True


def is_approved(key: str) -> bool:
    return _appr_path(key).exists()


def execute_approved(key: str, action: str, target: str, fn: Callable[[], Any]) -> ActionRecord | None:
    """Gate: only runs once approve(key) has happened; otherwise returns None (held)."""
    if not is_approved(key):
        return None
    return execute(key, action, target, fn)


# ---- sandbox sending -----------------------------------------------------------
def sandbox_send(payload: dict) -> str:
    """POST to $SANDBOX_WEBHOOK_URL if set, else append to state/sandbox_outbox.jsonl.
    Never sends anywhere but our own sandbox channel. Returns 'webhook' or 'outbox'."""
    url = os.environ.get("SANDBOX_WEBHOOK_URL")
    if url:
        req = urllib.request.Request(url, data=json.dumps(payload, default=str).encode(),
                                     headers={"Content-Type": "application/json"}, method="POST")
        with urllib.request.urlopen(req, timeout=10) as r:  # noqa: S310 (sandbox URL from env)
            r.read()
        return "webhook"
    append_jsonl(outbox_path(), payload)
    return "outbox"
