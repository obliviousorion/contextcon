"""SQLite state: step store, cost ledger, intent log, personas, facts, versioned beliefs.

One file (state/desk.sqlite by default, BD_STATE_DIR overrides). Every write commits at once,
so a kill at any point leaves a consistent database.
"""
from __future__ import annotations

import hashlib
import json
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]

SCHEMA = """
CREATE TABLE IF NOT EXISTS steps (
  key TEXT PRIMARY KEY, run_id TEXT, name TEXT, status TEXT, output TEXT, created_at TEXT);
CREATE TABLE IF NOT EXISTS ledger (
  id INTEGER PRIMARY KEY AUTOINCREMENT, ts TEXT, run_id TEXT, step TEXT, endpoint TEXT,
  credits REAL, inr REAL, cache_hit INTEGER, status TEXT, note TEXT);
CREATE TABLE IF NOT EXISTS intents (
  key TEXT PRIMARY KEY, run_id TEXT, action TEXT, persona_id TEXT, summary TEXT, payload TEXT,
  reversible INTEGER, cost_note TEXT, status TEXT, approved_by TEXT, approved_at TEXT,
  created_at TEXT, done_at TEXT, receipt TEXT);
CREATE TABLE IF NOT EXISTS personas (
  persona_id TEXT PRIMARY KEY, created_at TEXT, consent INTEGER, answers TEXT, signups INTEGER);
CREATE TABLE IF NOT EXISTS facts (
  persona_id TEXT, fact_id TEXT, statement TEXT, value TEXT, label TEXT, source TEXT,
  record_date TEXT, retrieved_at TEXT, PRIMARY KEY (persona_id, fact_id));
CREATE TABLE IF NOT EXISTS beliefs (
  group_key TEXT, belief_key TEXT, version INTEGER, statement TEXT, value REAL, n INTEGER,
  valid_from TEXT, valid_to TEXT, sources TEXT, PRIMARY KEY (group_key, belief_key, version));
CREATE TABLE IF NOT EXISTS runs (
  run_id TEXT PRIMARY KEY, request TEXT, status TEXT, started TEXT, finished TEXT, result TEXT);
CREATE TABLE IF NOT EXISTS watch_cursor (watch_id TEXT PRIMARY KEY, last_run_id TEXT, updated_at TEXT);
CREATE TABLE IF NOT EXISTS events (
  id INTEGER PRIMARY KEY AUTOINCREMENT, ts TEXT, run_id TEXT, step TEXT, status TEXT, msg TEXT);
"""


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def h(*parts: Any) -> str:
    """Stable short hash of any JSON-able inputs."""
    blob = json.dumps(parts, sort_keys=True, default=str, separators=(",", ":"))
    return hashlib.sha256(blob.encode()).hexdigest()[:16]


def state_dir() -> Path:
    d = Path(os.environ.get("BD_STATE_DIR") or ROOT / "state")
    d.mkdir(parents=True, exist_ok=True)
    return d


class Store:
    def __init__(self, path: Path | str | None = None):
        self.path = Path(path or state_dir() / "desk.sqlite")
        self.db = sqlite3.connect(self.path, isolation_level=None, timeout=30)
        self.db.row_factory = sqlite3.Row
        self.db.execute("PRAGMA journal_mode=WAL")
        self.db.execute("PRAGMA synchronous=FULL")
        self.db.executescript(SCHEMA)

    # ---- generic ----------------------------------------------------------
    def q(self, sql: str, *args) -> list[sqlite3.Row]:
        return self.db.execute(sql, args).fetchall()

    def x(self, sql: str, *args) -> None:
        self.db.execute(sql, args)

    # ---- steps ------------------------------------------------------------
    def step_get(self, key: str) -> Any | None:
        r = self.q("SELECT output FROM steps WHERE key=? AND status='done'", key)
        return json.loads(r[0]["output"]) if r else None

    def step_put(self, key: str, run_id: str, name: str, output: Any) -> None:
        self.x("INSERT OR REPLACE INTO steps VALUES (?,?,?,?,?,?)",
               key, run_id, name, "done", json.dumps(output, default=str), now())

    # ---- events (run console) --------------------------------------------
    def event(self, run_id: str, step: str, status: str, msg: str = "") -> None:
        self.x("INSERT INTO events (ts, run_id, step, status, msg) VALUES (?,?,?,?,?)",
               now(), run_id, step, status, msg)

    # ---- ledger -----------------------------------------------------------
    def ledger_add(self, run_id: str, step: str, endpoint: str, credits: float, inr: float,
                   cache_hit: bool, status: str, note: str = "") -> None:
        self.x("INSERT INTO ledger (ts, run_id, step, endpoint, credits, inr, cache_hit, status, note) "
               "VALUES (?,?,?,?,?,?,?,?,?)", now(), run_id, step, endpoint, credits, inr,
               int(cache_hit), status, note)

    def run_cost(self, run_id: str) -> dict:
        r = self.q("SELECT COALESCE(SUM(credits),0) c, COALESCE(SUM(inr),0) i, "
                   "SUM(CASE WHEN cache_hit=0 THEN 1 ELSE 0 END) calls, "
                   "SUM(CASE WHEN cache_hit=1 THEN 1 ELSE 0 END) hits FROM ledger WHERE run_id=?", run_id)[0]
        return {"credits": round(r["c"], 4), "inr": round(r["i"], 2), "calls": r["calls"] or 0,
                "cache_hits": r["hits"] or 0}

    def total_cost(self) -> dict:
        r = self.q("SELECT COALESCE(SUM(credits),0) c, COALESCE(SUM(inr),0) i FROM ledger")[0]
        return {"credits": round(r["c"], 4), "inr": round(r["i"], 2)}
