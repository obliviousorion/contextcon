"""Irreversible actions: application submission and cover-conversion request, to the sandbox only.

Protocol (exactly once across kills):
  1. prepare(): write the intent (status awaiting_approval) with an idempotency key = hash(action, persona, payload).
  2. approve(): a person flips awaiting_approval -> approved. A second click changes nothing.
  3. execute(): approved -> sending (committed) -> POST to sandbox with the key -> done (committed).
     On restart, an intent left in `sending` may or may not have reached the sandbox, so we ASK the
     sandbox first (GET /inbox?key=). Found -> mark done without resending. Sandbox unreachable ->
     hold; never send blind.
"""
from __future__ import annotations

import json
import urllib.error
import urllib.request

from .config import load_config, load_rules
from .store import Store, h, now


class SandboxDown(Exception):
    pass


def _sandbox() -> str:
    import os
    return (os.environ.get("BD_SANDBOX_URL") or load_config()["sandbox"]["url"]).rstrip("/")


def sandbox_count(key: str) -> int:
    try:
        with urllib.request.urlopen(f"{_sandbox()}/inbox?key={key}", timeout=5) as r:
            return int(json.loads(r.read())["count"])
    except (urllib.error.URLError, OSError, ValueError, KeyError) as e:
        raise SandboxDown(str(e))


def sandbox_send(key: str, action: str, payload: dict) -> dict:
    body = json.dumps({"key": key, "action": action, "payload": payload}).encode()
    req = urllib.request.Request(f"{_sandbox()}/inbox", data=body, method="POST",
                                 headers={"content-type": "application/json", "idempotency-key": key})
    try:
        with urllib.request.urlopen(req, timeout=5) as r:
            return json.loads(r.read())
    except (urllib.error.URLError, OSError) as e:
        raise SandboxDown(str(e))


def prepare(store: Store, run_id: str, action: str, persona_id: str, summary: str, payload: dict) -> dict:
    spec = load_rules()["actions"][action]
    key = f"{action}:{h(action, persona_id, payload)}"
    store.x("INSERT OR IGNORE INTO intents (key, run_id, action, persona_id, summary, payload, reversible, "
            "cost_note, status, created_at) VALUES (?,?,?,?,?,?,?,?,?,?)", key, run_id, action, persona_id,
            summary, json.dumps(payload), int(spec["reversible"]), spec["cost_note"], "awaiting_approval", now())
    return get(store, key)


def get(store: Store, key: str) -> dict | None:
    r = store.q("SELECT * FROM intents WHERE key=?", key)
    if not r:
        return None
    d = dict(r[0])
    d["payload"] = json.loads(d["payload"] or "{}")
    d["reversible"] = bool(d["reversible"])
    return d


def list_all(store: Store, run_id: str | None = None, persona_id: str | None = None) -> list[dict]:
    if persona_id:
        rows = store.q("SELECT key FROM intents WHERE run_id=? OR persona_id=? ORDER BY created_at DESC", run_id, persona_id)
    else:
        rows = store.q("SELECT key FROM intents " + ("WHERE run_id=? " if run_id else "") + "ORDER BY created_at DESC",
                       *([run_id] if run_id else []))
    return [get(store, r["key"]) for r in rows]


def approve(store: Store, key: str, approver: str) -> dict:
    cur = store.db.execute("UPDATE intents SET status='approved', approved_by=?, approved_at=? "
                           "WHERE key=? AND status='awaiting_approval'", (approver, now(), key))
    return {"approved": cur.rowcount == 1, "already": cur.rowcount == 0 and get(store, key) is not None}


def execute(store: Store, key: str, chaos=lambda where: None) -> dict:
    it = get(store, key)
    if not it or it["status"] in ("awaiting_approval", "done", "failed"):
        return it or {}
    if it["status"] == "sending":  # a previous attempt was cut off: did it land?
        if sandbox_count(key) > 0:
            store.x("UPDATE intents SET status='done', done_at=?, receipt=? WHERE key=?", now(),
                    "found in sandbox on restart; not resent", key)
            return get(store, key)
    store.x("UPDATE intents SET status='sending' WHERE key=? AND status IN ('approved','sending')", key)
    chaos("before_send")
    rec = sandbox_send(key, it["action"], it["payload"])
    chaos("after_send")
    store.x("UPDATE intents SET status='done', done_at=?, receipt=? WHERE key=?", now(),
            json.dumps(rec), key)
    return get(store, key)
