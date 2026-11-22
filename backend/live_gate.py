"""Replay first, live only after a person confirms the spend.

Every request is first answered from stored copies (a replay session: it cannot touch the network).
If that answers it, the result costs nothing. If it hit a cache miss and the server was started with
live enabled, the caller gets `needs_confirmation` with an estimate built from the recorded unit
prices, and nothing is spent. Re-sending with confirm runs the same request in live mode: the client
reads the cache first, calls Crustdata only for what is missing, and stores each response, so the same
company is never paid for twice. A per-session credit cap sits on top of the per-run cap in config.

The live cache lives in state/live-cache (gitignored), seeded from fixtures/live_check/cache, so the
committed fixtures never change.
"""
from __future__ import annotations

import asyncio
import json
import shutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Awaitable, Callable

from backend.crust.client import CrustClient
from backend.crust.ledger import CREDIT_TO_INR, Ledger
from backend.pipeline.session import (FIXTURE_CACHE, Session, cfg_get, load_yaml, recorded_unit_credits,
                                      set_session, state_dir)

_MISS_MARKERS = ("replay_miss", "cache miss (no network)")


def has_replay_miss(out: Any) -> bool:
    try:
        s = json.dumps(out.model_dump(mode="json") if hasattr(out, "model_dump") else out, default=str)
    except Exception:
        s = str(out)
    return any(m in s for m in _MISS_MARKERS)


def estimate_credits(kind: str) -> tuple[float, str]:
    """Upper-bound estimate from the recorded unit prices (identify 0.2/match, enrich 2.0/record)."""
    u = recorded_unit_credits()
    if kind == "resolve_domain":
        return u["identify"], "company/identify by domain (0.2 per match)"
    if kind == "resolve_name":
        return round(u["identify"] * 25, 2), "company/identify by name, up to 25 matches at 0.2 each"
    return round(u["identify"] + u["enrich"], 2), "company/identify (0.2) + company/enrich (2.0) for one company"


def _ledger_total(directory: Path) -> float:
    total = 0.0
    for f in directory.glob("*.jsonl"):
        total += Ledger(f.stem, directory).total
    return round(total, 6)


@dataclass
class LiveGate:
    live: bool = False
    session_cap: float = 10.0
    spent: float = 0.0
    lock: asyncio.Lock = field(default_factory=asyncio.Lock)
    _replay: Session | None = None
    _live: Session | None = None

    def __post_init__(self) -> None:
        self.cache_dir = state_dir() / "live-cache" if self.live else FIXTURE_CACHE
        if self.live:
            self.cache_dir.mkdir(parents=True, exist_ok=True)
            for f in FIXTURE_CACHE.glob("*.json"):  # seed: everything already recorded stays free
                dst = self.cache_dir / f.name
                if not dst.exists():
                    shutil.copy2(f, dst)
        self.ledger_dir = state_dir() / "ledger"

    def _session(self, mode: str) -> Session:
        cfg = load_yaml()
        client = CrustClient(run_id="http", mode=mode, cache_dir=self.cache_dir, ledger_dir=self.ledger_dir,
                             credit_cap=float(cfg_get(cfg, "limits", "credit_cap_per_run")),
                             time_limit=float(cfg_get(cfg, "limits", "time_limit_seconds")))
        return Session(client=client)

    @property
    def replay(self) -> Session:
        if self._replay is None:
            self._replay = self._session("replay")
        return self._replay

    @property
    def live_session(self) -> Session:
        if self._live is None:
            self._live = self._session("live")
        return self._live

    def status(self) -> dict:
        return {"live_enabled": self.live, "session_cap_credits": self.session_cap,
                "session_spent_credits": round(self.spent, 4),
                "session_left_credits": round(max(self.session_cap - self.spent, 0.0), 4)}

    async def run(self, fn: Callable[[], Awaitable[Any]], kind: str, confirm: bool) -> tuple[Any, dict | None]:
        """Returns (result, None) or (None, gate_info) when the caller must confirm (or cannot) spend."""
        async with self.lock:
            set_session(self.replay)
            try:
                out = await fn()
                if not has_replay_miss(out):
                    return out, None
                if not self.live:
                    return out, None  # replay-only server: show the honest refusal (source unavailable)
                est, basis = estimate_credits(kind)
                info = {"estimate_credits": est, "estimate_inr": round(est * CREDIT_TO_INR, 2), "basis": basis,
                        **self.status()}
                if not confirm:
                    return None, {"needs_confirmation": True,
                                  "reason": "Not in the stored copies. A live Crustdata lookup is needed.", **info}
                if self.spent + est > self.session_cap:
                    msg = (f"Session credit cap {self.session_cap:g} would be exceeded "
                                            f"(spent {self.spent:g}, estimate {est:g}). Restart the server with a "
                                            "higher --cap to continue.")
                    return None, {"needs_confirmation": False, "blocked": True, "reason": msg, "error": msg, **info}
                before = _ledger_total(self.ledger_dir)
                set_session(self.live_session)
                out = await fn()
                self.spent += max(_ledger_total(self.ledger_dir) - before, 0.0)
                self._replay = None  # next probe re-reads the cache, now holding what was just fetched
                return out, None
            finally:
                set_session(self.replay)
