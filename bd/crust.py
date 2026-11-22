"""Thin Crustdata client: disk cache by request hash, record/replay, cost ledger, caps, retries.

- replay: answer only from cache (state/cache) or committed fixtures (fixtures/crust); a miss is
  reported as `replay_miss`, never guessed, and costs nothing.
- record/live: call the API; record also writes the response to the cache.
- Every call (cache hits included, at 0 credits) is one row in the SQLite ledger.
- A call that would cross the run's credit cap, or start after the time limit, is not sent:
  the client returns kind="held" and the run stops cleanly.
- Timeouts, 429 and 5xx: exponential backoff with full jitter, up to limits.max_retries.
- Logs carry endpoint and request hash only, never names or profile URLs.
"""
from __future__ import annotations

import json
import logging
import os
import random
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import httpx
from dotenv import load_dotenv

from .config import load_config
from .store import ROOT, Store, h, now, state_dir

log = logging.getLogger("bd.crust")
load_dotenv(ROOT / ".env")

FIXTURE_DIR = ROOT / "fixtures" / "crust"


@dataclass
class Result:
    ok: bool
    kind: str = "ok"          # ok | empty | held | replay_miss | error | removed
    status: int | None = None
    data: Any = None
    credits: float = 0.0
    cache_hit: bool = False
    retrieved_at: str | None = None
    endpoint: str = ""
    req_hash: str = ""
    reason: str = ""
    extra: dict = field(default_factory=dict)


class Held(Exception):
    """Raised by callers that must stop the run cleanly (cap or time limit)."""


_LAST_CALL = [0.0]
MIN_INTERVAL = 2.1  # seconds between network calls: stays under the 30/min endpoint limit


class Crust:
    def __init__(self, store: Store, run_id: str, step: str = "-", mode: str | None = None,
                 credit_cap: float | None = None, started: float | None = None,
                 transport: httpx.BaseTransport | None = None, sleep=time.sleep):
        cfg = load_config()
        self.cfg = cfg
        self.store, self.run_id, self.step = store, run_id, step
        self.mode = (mode or os.environ.get("BD_MODE") or cfg["mode"]).lower()
        self.cap = float(credit_cap if credit_cap is not None else cfg["limits"]["credit_cap_per_run"])
        self.time_limit = float(cfg["limits"]["time_limit_seconds"])
        self.started = started or time.time()
        self.cache_dir = state_dir() / "cache"
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.transport, self.sleep = transport, sleep
        self.use_cache = True  # the live smoke test turns this off
        self.prices = cfg["cost"]["prices"]
        self.inr = float(cfg["cost"]["inr_per_credit"])

    # ---- cache ------------------------------------------------------------
    def _cache_paths(self, key: str) -> list[Path]:
        return [self.cache_dir / f"{key}.json", FIXTURE_DIR / f"{key}.json"]

    def _cache_get(self, key: str) -> dict | None:
        for p in self._cache_paths(key):
            if p.exists():
                try:
                    return json.loads(p.read_text())
                except json.JSONDecodeError:
                    continue
        return None

    def _cache_put(self, key: str, path: str, status: int, data: Any, credits: float) -> str:
        ts = now()
        tmp = self.cache_dir / f"{key}.json.tmp"
        tmp.write_text(json.dumps({"endpoint": path, "status": status, "retrieved_at": ts,
                                   "credits": credits, "data": data}))
        os.replace(tmp, self.cache_dir / f"{key}.json")
        return ts

    # ---- cost -------------------------------------------------------------
    def estimate(self, path: str, body: dict) -> float:
        p = self.prices.get(path, {"credits": 0})
        if p.get("per") == "result":
            return p["credits"] * int(body.get("limit", 20) or 0)
        if p.get("per") in ("record", "match"):
            n = len(body.get("professional_network_profile_urls") or body.get("domains")
                    or body.get("crustdata_company_ids") or [1])
            return p["credits"] * n
        if p.get("per") == "url":
            return p["credits"] * len(body.get("urls") or [1])
        return float(p.get("credits", 0))

    def charged(self, path: str, body: dict, data: Any, headers) -> float:
        for k in ("x-credits-used", "x-credits-consumed", "x-credit-cost", "x-credits-charged"):
            v = headers.get(k) if headers is not None else None
            if v is not None:
                try:
                    return float(v)
                except ValueError:
                    pass
        p = self.prices.get(path, {"credits": 0})
        per, c = p.get("per"), float(p.get("credits", 0))
        if per == "result":
            rows = []
            if isinstance(data, dict):
                rows = data.get("job_listings") or data.get("profiles") or data.get("companies") or []
            return round(c * len(rows), 4)
        if per in ("record", "match"):
            items = data if isinstance(data, list) else []
            return round(c * sum(1 for i in items if isinstance(i, dict) and i.get("matches")), 4)
        if per == "url":
            return c * len(body.get("urls") or [])
        return c

    # ---- core -------------------------------------------------------------
    def call(self, path: str, body: dict | None = None, method: str = "POST",
             cacheable: bool = True) -> Result:
        body = body or {}
        key = h(method, path, body)
        cached = self._cache_get(key) if cacheable and self.use_cache else None
        if cached is not None:
            self.store.ledger_add(self.run_id, self.step, path, 0.0, 0.0, True, "cache", key)
            return self._wrap(path, key, cached["status"], cached["data"], 0.0, True, cached.get("retrieved_at"))
        if self.mode == "replay":
            self.store.ledger_add(self.run_id, self.step, path, 0.0, 0.0, False, "replay_miss", key)
            return Result(False, "replay_miss", endpoint=path, req_hash=key,
                          reason=f"no recorded response for {path} (replay mode)")
        spent = self.store.run_cost(self.run_id)["credits"]
        est = self.estimate(path, body)
        if spent + est > self.cap + 1e-9:
            self.store.ledger_add(self.run_id, self.step, path, 0.0, 0.0, False, "held", key)
            return Result(False, "held", endpoint=path, req_hash=key,
                          reason=f"credit cap {self.cap} would be crossed (spent {spent:.2f}, next ~{est:.2f})")
        if time.time() - self.started > self.time_limit:
            self.store.ledger_add(self.run_id, self.step, path, 0.0, 0.0, False, "held", key)
            return Result(False, "held", endpoint=path, req_hash=key,
                          reason=f"time limit {self.time_limit:.0f}s reached")
        return self._network(method, path, body, key, cacheable)

    def _network(self, method: str, path: str, body: dict, key: str, cacheable: bool) -> Result:
        api_key = os.environ.get("CRUST_KEY")
        if not api_key:
            return Result(False, "error", endpoint=path, req_hash=key, reason="CRUST_KEY not set")
        cc = self.cfg["crustdata"]
        headers = {"authorization": f"Bearer {api_key}", "x-api-version": cc["api_version"],
                   "content-type": "application/json"}
        retries = int(self.cfg["limits"]["max_retries"])
        last = ""
        with httpx.Client(base_url=cc["base_url"], timeout=cc["timeout_seconds"],
                          transport=self.transport) as http:
            for attempt in range(retries + 1):
                gap = MIN_INTERVAL - (time.time() - _LAST_CALL[0])
                if gap > 0 and self.transport is None:
                    self.sleep(gap)
                _LAST_CALL[0] = time.time()
                try:
                    r = http.request(method, path, headers=headers,
                                     json=body if method != "GET" else None)
                except (httpx.TimeoutException, httpx.TransportError) as e:
                    last = f"{type(e).__name__}"
                    self._backoff(attempt, None)
                    continue
                if r.status_code == 429 or r.status_code >= 500:
                    last = f"HTTP {r.status_code}"
                    self._backoff(attempt, r.headers.get("x-ratelimit-reset"))
                    continue
                try:
                    data = r.json()
                except ValueError:
                    data = None
                if r.status_code >= 400:
                    self.store.ledger_add(self.run_id, self.step, path, 0.0, 0.0, False,
                                          f"http_{r.status_code}", key)
                    return Result(False, "error", r.status_code, data, endpoint=path, req_hash=key,
                                  reason=f"HTTP {r.status_code}: {json.dumps(data)[:300]}")
                credits = self.charged(path, body, data, r.headers)
                ts = self._cache_put(key, path, r.status_code, data, credits) if (
                    cacheable and self.mode in ("record", "live")) else now()
                self.store.ledger_add(self.run_id, self.step, path, credits, round(credits * self.inr, 2),
                                      False, "ok", key)
                return self._wrap(path, key, r.status_code, data, credits, False, ts)
        self.store.ledger_add(self.run_id, self.step, path, 0.0, 0.0, False, "failed", f"{key} {last}")
        return Result(False, "error", endpoint=path, req_hash=key,
                      reason=f"gave up after {retries + 1} attempts ({last}); step held, not read as an answer")

    def _backoff(self, attempt: int, reset: str | None) -> None:
        wait = min(30.0, 1.0 * (2 ** attempt))
        try:
            if reset is not None:
                wait = max(wait, min(60.0, float(reset)))
        except ValueError:
            pass
        self.sleep(random.uniform(0, wait))  # full jitter

    @staticmethod
    def _wrap(path, key, status, data, credits, hit, ts) -> Result:
        empty = (isinstance(data, dict) and not (data.get("job_listings") or data.get("profiles"))
                 and "total_count" in data and not data.get("total_count")) or data == []
        return Result(True, "empty" if empty else "ok", status, data, credits, hit, ts, path, key)

    # ---- endpoints --------------------------------------------------------
    def person_enrich(self, url: str) -> Result:
        return self.call("/person/enrich", {"professional_network_profile_urls": [url],
                                            "fields": ["basic_profile", "experience"]})

    def job_search(self, body: dict) -> Result:
        return self.call("/job/search", body)

    def person_search(self, body: dict) -> Result:
        return self.call("/person/search", body)

    def company_identify(self, domain: str) -> Result:
        return self.call("/company/identify", {"domains": [domain]})

    def web_fetch(self, url: str) -> Result:
        return self.call("/web/enrich/live", {"urls": [url]})

    def web_search(self, query: str) -> Result:
        return self.call("/web/search/live", {"query": query})
