"""Async Crustdata client: cache, rate limit, retry, ledger, budget. Never raises on bad responses."""
from __future__ import annotations

import asyncio
import json
import logging
import os
import time
from pathlib import Path
from typing import Any, Awaitable, Callable

import httpx

from .cache import DiskCache, cache_key, now_iso
from .ledger import DEFAULT_CREDIT_CAP, PRICES, Ledger
from .limiter import RateLimiter
from .results import CrustResult, EndpointDisabled, first_list, parse_company_enrich, unavailable

log = logging.getLogger("crust")
BASE_URL = "https://api.crustdata.com"
API_VERSION = "2025-11-01"
BACKOFF = (1, 2, 4)
MAX_WAIT = 60.0

try:  # key comes from env; loading ../.env is fine, never printed
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parents[3] / ".env")
    load_dotenv()
except Exception:  # pragma: no cover
    pass


class CrustClient:
    def __init__(self, run_id: str = "default", mode: str | None = None, api_key: str | None = None,
                 cache_dir=None, ledger_dir=None, credit_cap: float = DEFAULT_CREDIT_CAP,
                 time_limit: float | None = None, timeout: float = 30.0, base_url: str = BASE_URL,
                 limiter: RateLimiter | None = None, sleep: Callable[[float], Awaitable] = asyncio.sleep,
                 clock: Callable[[], float] = time.time, http: httpx.AsyncClient | None = None):
        self.run_id = run_id
        self.mode = (mode or os.environ.get("MODE") or "live").lower()
        if self.mode not in ("live", "record", "replay"):
            raise ValueError(f"bad MODE {self.mode!r}")
        self.api_key = api_key or os.environ.get("CRUST_KEY")
        self.cache = DiskCache(cache_dir)
        self.ledger = Ledger(run_id, ledger_dir)
        self.credit_cap, self.time_limit = credit_cap, time_limit
        self.timeout, self.base_url = timeout, base_url
        self.limiter = limiter or RateLimiter()
        self.sleep, self.clock = sleep, clock
        self._started = clock()
        self._http = http
        self._inflight: dict[str, asyncio.Future] = {}
        self.network_calls = 0
        self.hard_stop: CrustResult | None = None  # set on 402
        self.held: str | None = None  # resumable hold reason

    # ---- budget -------------------------------------------------------------
    def get_run_cost(self) -> float:
        return self.ledger.total

    def resume(self, credit_cap: float | None = None, time_limit: float | None = None) -> None:
        """Clear a held state (optionally raising the cap / extending time) and continue."""
        if credit_cap is not None:
            self.credit_cap = credit_cap
        if time_limit is not None:
            self.time_limit = time_limit
            self._started = self.clock()
        self.held = None

    def _budget_block(self, path: str, body: Any) -> CrustResult | None:
        reason = None
        est = self._estimate(path, body)
        if self.ledger.total + est > self.credit_cap:
            reason = (f"credit cap {self.credit_cap} would be exceeded "
                      f"(spent {self.ledger.total:.2f}, est +{est:.2f})")
        elif self.time_limit is not None and self.clock() - self._started > self.time_limit:
            reason = f"time limit {self.time_limit}s reached"
        if reason:
            self.held = reason
            return unavailable(path, "held: " + reason, kind="held")
        return None

    @staticmethod
    def _estimate(path: str, body: Any) -> float:
        b = body if isinstance(body, dict) else {}
        if path == "/company/enrich":
            n = sum(len(b.get(k) or []) for k in ("crustdata_company_ids", "domains", "names")) or 1
            return 2.0 * n
        if path == "/company/search":
            return 0.03 * int(b.get("limit") or 1)
        if path == "/web/enrich/live":
            return PRICES[path] * (len(b.get("urls") or []) or 1)
        return PRICES.get(path, 0.0)

    @staticmethod
    def _credits(path: str, headers, data: Any, body: Any) -> float:
        for h in ("x-credits-used", "x-credits-consumed", "x-credit-cost", "x-credits-charged"):
            try:
                v = headers.get(h)
                if v is not None:
                    return float(v)
            except (ValueError, TypeError):
                pass
        if isinstance(data, dict):
            for k in ("credits_used", "credits_consumed", "credit_cost"):
                if isinstance(data.get(k), (int, float)):
                    return float(data[k])
        price = PRICES.get(path)
        if price is None:
            return 0.0
        if path == "/web/search/live":
            return price
        if path == "/web/enrich/live":
            return price * (len((body or {}).get("urls") or []) if isinstance(body, dict) else 1)
        if path == "/company/enrich":
            n = sum(len((i or {}).get("matches") or []) for i in first_list(data) if isinstance(i, dict))
            return price * (n or (len(first_list(data)) if first_list(data) else 0))
        if path == "/company/identify":
            n = sum(len((i or {}).get("matches") or []) for i in first_list(data) if isinstance(i, dict))
            return price * n
        return price * len(first_list(data))

    # ---- core ---------------------------------------------------------------
    async def request(self, method: str, path: str, body: Any = None, *, group: str | None = None,
                      max_age: float | None = None, cacheable: bool = True) -> CrustResult:
        try:
            key = cache_key(f"{method} {path}", body)
            fut = self._inflight.get(key)
            if fut is not None:  # dedupe identical in-flight requests
                res = await asyncio.shield(fut)
                if res.ok:
                    self.ledger.add(path, 0.0, True)
                return res
            fut = asyncio.get_running_loop().create_future()
            self._inflight[key] = fut
            try:
                res = await self._execute(method, path, body, key, group, max_age, cacheable)
            except Exception as e:  # never raise to callers
                res = unavailable(path, f"internal error: {type(e).__name__}: {e}", key=key)
            fut.set_result(res)
            self._inflight.pop(key, None)
            return res
        except Exception as e:
            return unavailable(path, f"internal error: {type(e).__name__}: {e}")

    async def _execute(self, method, path, body, key, group, max_age, cacheable) -> CrustResult:
        if cacheable and self.mode != "record":
            entry = self.cache.get(key, None if self.mode == "replay" else max_age)
            if entry:
                self.ledger.add(path, 0.0, True)
                return CrustResult(ok=True, status=entry.get("status", 200), data=entry["response"],
                                   retrieved_at=entry.get("retrieved_at"), cache_hit=True,
                                   cache_key=key, endpoint=path)
        if self.mode == "replay":
            return unavailable(path, "replay mode: cache miss (no network)", kind="replay_miss", key=key)
        if self.hard_stop is not None:
            return self.hard_stop
        blocked = self._budget_block(path, body)
        if blocked is not None:
            blocked.cache_key = key
            return blocked
        if not self.api_key:
            return unavailable(path, "CRUST_KEY not set", key=key)
        iid = self.ledger.intent(path, self._estimate(path, body))  # durable before the call
        try:
            res = await self._network(method, path, body, key, group)
        except BaseException:
            raise  # intent stays pending: a possibly-billed call is never forgotten
        if res.ok:
            self.ledger.add(path, res.credits, False, iid)  # ledger first: never undercount
            if cacheable:
                self.cache.put(key, {"method": method, "path": path, "body": body}, res.data, res.status or 200)
        else:
            self.ledger.release(iid)
        return res

    def _headers(self) -> dict:
        return {"authorization": f"Bearer {self.api_key}", "x-api-version": API_VERSION,
                "content-type": "application/json"}

    @staticmethod
    def _reset_wait(headers) -> float | None:
        v = headers.get("x-ratelimit-reset")
        if v is None:
            return None
        try:
            f = float(v)
        except ValueError:
            return None
        if f > 1e9:  # epoch seconds
            f -= time.time()
        return min(max(f, 0.0), MAX_WAIT)

    async def _network(self, method, path, body, key, group) -> CrustResult:
        http = self._http or httpx.AsyncClient(base_url=self.base_url, timeout=self.timeout)
        try:
            last = "no attempt"
            for attempt in range(len(BACKOFF) + 1):
                await self.limiter.acquire(group)
                self.network_calls += 1
                wait = None
                try:
                    kw = {"json": body} if body is not None and method != "GET" else {}
                    r = await http.request(method, self._url(path), headers=self._headers(),
                                           timeout=self.timeout, **kw)
                except httpx.HTTPError as e:
                    last = f"transport error: {type(e).__name__}"
                    r = None
                if r is not None:
                    s = r.status_code
                    if s == 402:
                        self.hard_stop = unavailable(path, "402 payment required: out of credits; stopping, no retry",
                                                     402, "payment_required", key)
                        return self.hard_stop
                    if s == 403:
                        return EndpointDisabled(ok=False, kind="endpoint_disabled", status=403, endpoint=path,
                                                reason=f"endpoint disabled for this account: {path}", cache_key=key)
                    if s == 429 or s >= 500:
                        last = f"HTTP {s}"
                        wait = self._reset_wait(r.headers) if s == 429 else None
                    elif 200 <= s < 300:
                        try:
                            data = r.json()
                        except ValueError:
                            return unavailable(path, "malformed response: not JSON", s, key=key)
                        if path == "/company/enrich" and not parse_company_enrich(data):
                            return unavailable(path, "malformed response: no parseable company record "
                                               "(not cached, not billed)", s, key=key)
                        return CrustResult(ok=True, status=s, data=data, retrieved_at=now_iso(), endpoint=path,
                                           credits=self._credits(path, r.headers, data, body), cache_key=key)
                    else:
                        return unavailable(path, f"HTTP {s}", s, key=key)
                if attempt < len(BACKOFF):
                    await self.sleep(wait if wait is not None else BACKOFF[attempt])
            return unavailable(path, f"retries exhausted ({last})", key=key)
        finally:
            if self._http is None:
                await http.aclose()

    def _url(self, path: str) -> str:
        return self.base_url + path if self._http is not None else path

    # ---- endpoints ----------------------------------------------------------
    async def permissions(self, **kw):
        return await self.request("GET", "/account/endpoints?status=disabled", cacheable=False, **kw)

    async def credits(self, **kw):
        return await self.request("GET", "/account/credits", cacheable=False, **kw)

    async def company_identify(self, body, **kw):
        return await self.request("POST", "/company/identify", body, group="enrich", **kw)

    async def company_enrich(self, body, **kw):
        return await self.request("POST", "/company/enrich", body, group="enrich", **kw)

    async def company_search(self, body, **kw):
        return await self.request("POST", "/company/search", body, group="search", **kw)

    async def person_search(self, body, **kw):
        return EndpointDisabled(ok=False, kind="endpoint_disabled", endpoint="/person/search",
                                reason="personal data not used by AsOf")  # no network, ever

    async def person_enrich(self, body, **kw):
        return EndpointDisabled(ok=False, kind="endpoint_disabled", endpoint="/person/enrich",
                                reason="personal data not used by AsOf")  # no network, ever

    async def job_search(self, body, **kw):
        return await self.request("POST", "/job/search", body, group="job", **kw)

    async def web_search(self, body, **kw):
        return await self.request("POST", "/web/search/live", body, group="web", **kw)

    async def web_fetch(self, body, **kw):
        # /web/fetch returns 404; the docs' page fetch is /web/enrich/live (measured 2026-11-22, 1 credit/page)
        return await self.request("POST", "/web/enrich/live", body, group="web", **kw)

    async def autocomplete(self, body, kind: str = "company", **kw):
        # path UNVERIFIED; see NOTES.md
        return await self.request("POST", f"/{kind}/search/autocomplete", body, group="search", **kw)

    async def watch_create(self, body, **kw):
        return await self.request("POST", "/watch/company/search", body, group="watch", cacheable=False, **kw)

    async def watch_test(self, watch_id: str, **kw):
        return await self.request("POST", f"/watch/company/search/{watch_id}/test", {}, group="watch",
                                  cacheable=False, **kw)


def _disabled_names(data: Any) -> list[str]:
    items = first_list(data, "endpoints", "disabled", "results", "data")
    out = []
    for i in items:
        if isinstance(i, str):
            out.append(i)
        elif isinstance(i, dict):
            n = i.get("endpoint") or i.get("path") or i.get("name")
            if n:
                out.append(str(n))
    return out


async def check_disabled_endpoints(client: CrustClient) -> list[str]:
    """Startup helper: log disabled endpoints. Returns [] if unavailable."""
    res = await client.permissions()
    if not res.ok:
        log.warning("could not check endpoint permissions: %s", res.reason)
        return []
    names = _disabled_names(res.data)
    for n in names:
        log.warning("Crustdata endpoint DISABLED for this account: %s", n)
    if not names:
        log.info("no disabled Crustdata endpoints")
    return names
