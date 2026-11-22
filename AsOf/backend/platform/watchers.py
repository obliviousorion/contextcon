"""Watchers: create (held for approval, tagged with idempotency key), /test (free), poll, dedupe."""
from __future__ import annotations

import hashlib
import json
from datetime import date
from typing import Any

from backend.models import WatchSnapshot

from . import actions
from .config import load_config, state_dir
from .util import append_jsonl, atomic_write_json, read_json, read_jsonl


def idempotency_key(domain: str) -> str:
    return "watch:" + hashlib.sha256(f"create_watcher|{domain.lower()}".encode()).hexdigest()[:16]


def dedupe_key(watch_id: str, company_id: int, field: str, signal_date: date | str) -> str:
    return hashlib.sha256(f"{watch_id}|{company_id}|{field}|{signal_date}".encode()).hexdigest()


def _reg():
    return state_dir() / "watchers.json"


def _alerts():
    return state_dir() / "watch_alerts.jsonl"


def _registry() -> dict:
    d = read_json(_reg())
    return d if isinstance(d, dict) else {}


def create(domain: str, company_id: int | None = None, field: str = "headcount") -> dict:
    """Step 1: record a held creation request tagged with its idempotency key (no credit spend,
    no external effect). Returns {'key', 'status': 'held_for_approval'|'created', 'watch_id'}."""
    key = idempotency_key(domain)
    reg = _registry()
    ent = reg.get(key) or {"key": key, "domain": domain, "company_id": company_id, "field": field,
                           "watch_id": None, "status": "held_for_approval"}
    reg[key] = ent
    atomic_write_json(_reg(), reg)
    return ent


def activate(key: str, create_fn) -> dict:
    """After approve(key): run create_fn() -> watch_id exactly once and save it under the key."""
    reg = _registry()
    ent = reg.get(key)
    if ent is None:
        raise KeyError(key)
    if ent["status"] == "created":
        return ent
    def _create():
        wid = str(create_fn())
        r = _registry()
        r[key] = {**r.get(key, ent), "watch_id": wid}
        atomic_write_json(_reg(), r)  # saved inside the once-only effect

    rec = actions.execute_approved(key, "create_watcher", ent["domain"], _create)
    if rec is None:
        return ent  # still held
    ent = {**_registry().get(key, ent), "status": "created"}
    reg = _registry()
    reg[key] = ent
    atomic_write_json(_reg(), reg)
    return ent


def test(watch_id: str) -> dict:
    """/test is free: synthesises nothing external; returns a well-formed dry-run alert."""
    return {"watch_id": watch_id, "cost_credits": 0.0, "ok": True}


def on_alert(watch_id: str, company_id: int, field: str, signal_date: date, snapshot_hash: str,
             stale_line_ids: list[str] | None = None) -> tuple[WatchSnapshot, bool]:
    """Returns (WatchSnapshot, is_new). A duplicate delivery is a no-op (is_new False)."""
    dk = dedupe_key(watch_id, company_id, field, signal_date)
    snap = WatchSnapshot(watch_id=watch_id, crustdata_company_id=company_id, field=field,
                         signal_date=signal_date, snapshot_hash=snapshot_hash, dedupe_key=dk,
                         stale_line_ids=stale_line_ids or [])
    seen = read_jsonl(_alerts())
    for e in seen:
        if e.get("dedupe_key") == dk:
            return WatchSnapshot(**e), False
    cap = load_config().get("watch", {}).get("max_alerts_per_entity_per_month", 2)
    month = str(signal_date)[:7]
    n = sum(1 for e in seen if e["crustdata_company_id"] == company_id and str(e["signal_date"])[:7] == month)
    if n >= cap:
        return snap, False  # monthly alert cap: not recorded, not re-attested
    append_jsonl(_alerts(), json.loads(snap.model_dump_json()))
    return snap, True


def poll(fetch_runs, watch_id: str, company_id: int) -> list[tuple[WatchSnapshot, bool]]:
    """fetch_runs(watch_id) -> iterable of dicts {field, signal_date, snapshot_hash, stale_line_ids?}.
    Pull-based, so no tunnel is needed. Each is routed through on_alert (deduped)."""
    out = []
    for r in fetch_runs(watch_id) or []:
        sd = r["signal_date"]
        sd = sd if isinstance(sd, date) else date.fromisoformat(str(sd)[:10])
        out.append(on_alert(watch_id, company_id, r["field"], sd, r.get("snapshot_hash", ""),
                            r.get("stale_line_ids")))
    return out
