import asyncio
import json
from pathlib import Path

import httpx
import pytest
import respx

from backend.crust import CrustClient, EndpointDisabled, FilterError, build_filter, check_disabled_endpoints, parse_company_enrich
from backend.crust.cache import DiskCache, cache_key
from backend.crust.ledger import get_run_cost
from backend.crust.limiter import RateLimiter, TokenBucket

BASE = "https://api.crustdata.com"
FIXTURE = Path(__file__).parents[3] / "fixtures/live_check/enrich.json"


async def nosleep(s):
    nosleep.calls.append(s)
nosleep.calls = []


@pytest.fixture(autouse=True)
def _reset():
    nosleep.calls.clear()


def mk(tmp_path, mode="live", run="r1", **kw):
    return CrustClient(run_id=run, mode=mode, api_key="k", cache_dir=tmp_path / "c", ledger_dir=tmp_path / "l",
                       sleep=nosleep, limiter=RateLimiter(capacity=1000), **kw)


ENRICH = {"domains": ["reo.dev"]}


@respx.mock
async def test_replay_zero_network_and_miss_is_error(tmp_path):
    route = respx.post(f"{BASE}/company/enrich").mock(return_value=httpx.Response(200, json=[]))
    c = mk(tmp_path, "replay")
    r = await c.company_enrich(ENRICH)
    assert not r.ok and r.kind == "replay_miss"
    assert route.call_count == 0 and c.network_calls == 0
    # seed the cache, then replay hits it
    key = cache_key("POST /company/enrich", ENRICH)
    DiskCache(tmp_path / "c").put(key, {}, [{"x": 1}], 200)
    r = await c.company_enrich(ENRICH)
    assert r.ok and r.cache_hit and r.data == [{"x": 1}] and r.retrieved_at
    assert route.call_count == 0


@respx.mock
async def test_non_2xx_never_cached(tmp_path):
    respx.post(f"{BASE}/company/search").mock(return_value=httpx.Response(400, json={"e": 1}))
    c = mk(tmp_path)
    r = await c.company_search({"q": 1})
    assert not r.ok
    assert not list((tmp_path / "c").glob("*.json")) if (tmp_path / "c").exists() else True
    assert DiskCache(tmp_path / "c").put("k", {}, {}, 500) is None


async def test_limiter_spacing():
    t = [0.0]
    slept = []

    async def sl(s):
        slept.append(s)
        t[0] += s
    b = TokenBucket(30, capacity=1, clock=lambda: t[0], sleep=sl)
    for _ in range(4):
        await b.acquire()
    assert slept == [pytest.approx(2.0)] * 3  # 30/min => 2s spacing
    assert t[0] == pytest.approx(6.0)


def test_filters_no_gte_lte():
    f = build_filter("and", [("year_founded", "=>", 2020), ("hc", "=<", 50),
                             {"op": "or", "conditions": [{"field": "c", "type": "in", "value": ["US"]},
                                                         {"field": "d", "type": "is_null"}]}])
    s = json.dumps(f)
    assert ">=" not in s.replace("=>", "") and "<=" not in s
    assert "=>" in s and "=<" in s
    for bad in (">=", "<="):
        with pytest.raises(FilterError):
            build_filter("and", [("a", bad, 1)])
    with pytest.raises(FilterError):
        build_filter("and", [("a", "like", 1)])


@respx.mock
async def test_429_honors_reset_header(tmp_path):
    route = respx.post(f"{BASE}/company/search").mock(side_effect=[
        httpx.Response(429, headers={"x-ratelimit-reset": "7"}), httpx.Response(200, json={"results": []})])
    r = await mk(tmp_path).company_search({"q": 1})
    assert r.ok and route.call_count == 2 and nosleep.calls == [7.0]


@respx.mock
async def test_5xx_backoff_then_exhaust(tmp_path):
    route = respx.post(f"{BASE}/job/search").mock(return_value=httpx.Response(503))
    r = await mk(tmp_path).job_search({"q": 1})
    assert not r.ok and route.call_count == 4 and nosleep.calls == [1, 2, 4]


@respx.mock
async def test_402_stops_no_retry(tmp_path):
    route = respx.post(f"{BASE}/company/enrich").mock(return_value=httpx.Response(402))
    c = mk(tmp_path)
    r = await c.company_enrich(ENRICH)
    assert r.kind == "payment_required" and route.call_count == 1 and not nosleep.calls
    r2 = await c.company_search({"q": 1})  # hard stop persists, no network
    assert r2.kind == "payment_required" and route.call_count == 1


@respx.mock
async def test_403_endpoint_disabled(tmp_path):
    respx.post(f"{BASE}/web/fetch").mock(return_value=httpx.Response(403))
    r = await mk(tmp_path).web_fetch({"url": "x"})
    assert isinstance(r, EndpointDisabled) and not r.ok and r.status == 403


@respx.mock
async def test_malformed_unavailable(tmp_path):
    respx.post(f"{BASE}/company/enrich").mock(return_value=httpx.Response(200, content=b"<html>"))
    c = mk(tmp_path)
    r = await c.company_enrich(ENRICH)
    assert not r.ok and r.kind == "unavailable" and "malformed" in r.reason
    assert parse_company_enrich({"weird": 1}) == [] and parse_company_enrich(None) == []
    assert parse_company_enrich([{"matches": [None, {"company_data": 3}]}]) == []


@respx.mock
async def test_ledger_totals_and_cache_hits_free(tmp_path):
    data = json.loads(FIXTURE.read_text())["data"][:2]
    respx.post(f"{BASE}/company/enrich").mock(return_value=httpx.Response(200, json=data))
    respx.post(f"{BASE}/web/search/live").mock(return_value=httpx.Response(200, json={"results": []}))
    c = mk(tmp_path)
    r = await c.company_enrich(ENRICH)
    n = len(parse_company_enrich(data))
    assert n >= 1 and r.credits == 2.0 * sum(len(i["matches"]) for i in data)
    await c.company_enrich(ENRICH)  # cache hit
    await c.web_search({"query": "x"})
    es = c.ledger.entries
    assert [e.cache_hit for e in es] == [False, True, False]
    assert es[1].credits == 0 and c.get_run_cost() == r.credits + 1.0
    assert get_run_cost("r1", tmp_path / "l") == c.get_run_cost()


@respx.mock
async def test_header_credits_override(tmp_path):
    respx.post(f"{BASE}/company/search").mock(return_value=httpx.Response(200, json={"results": [1, 2]},
                                                                          headers={"x-credits-used": "5"}))
    r = await mk(tmp_path).company_search({"q": 1})
    assert r.credits == 5.0


@respx.mock
async def test_resume_after_crash_zero_network(tmp_path):
    data = json.loads(FIXTURE.read_text())["data"][:1]
    route = respx.post(f"{BASE}/company/enrich").mock(return_value=httpx.Response(200, json=data))
    c1 = mk(tmp_path)
    await c1.company_enrich(ENRICH)
    cost = c1.get_run_cost()
    assert cost == 2.0 * len(data[0]["matches"]) and route.call_count == 1
    c2 = mk(tmp_path)  # simulated restart, same run_id
    r = await c2.company_enrich(ENRICH)
    assert r.cache_hit and route.call_count == 1 and c2.network_calls == 0
    assert c2.get_run_cost() == cost


@respx.mock
async def test_inflight_dedupe(tmp_path):
    async def slow(request):
        await asyncio.sleep(0.05)
        return httpx.Response(200, json={"results": [1]})
    route = respx.post(f"{BASE}/company/search").mock(side_effect=slow)
    c = mk(tmp_path)
    rs = await asyncio.gather(*[c.company_search({"q": 1}) for _ in range(5)])
    assert route.call_count == 1 and all(r.ok for r in rs)
    assert sum(e.credits for e in c.ledger.entries) == pytest.approx(0.03)


@respx.mock
async def test_budget_cap_holds_and_resumes(tmp_path):
    route = respx.post(f"{BASE}/web/search/live").mock(return_value=httpx.Response(200, json={}))
    c = mk(tmp_path, credit_cap=2.0)
    assert (await c.web_search({"query": "a"})).ok
    assert (await c.web_search({"query": "b"})).ok
    r = await c.web_search({"query": "c"})
    assert r.kind == "held" and c.held and route.call_count == 2
    assert (await c.web_search({"query": "a"})).cache_hit  # cache still served while held
    c.resume(credit_cap=10)
    assert (await c.web_search({"query": "c"})).ok and route.call_count == 3


@respx.mock
async def test_max_age_forces_refresh(tmp_path):
    route = respx.post(f"{BASE}/web/search/live").mock(return_value=httpx.Response(200, json={}))
    c = mk(tmp_path)
    await c.web_search({"query": "a"})
    await c.web_search({"query": "a"}, max_age=3600)
    assert route.call_count == 1
    await c.web_search({"query": "a"}, max_age=-1)
    assert route.call_count == 2


@respx.mock
async def test_startup_disabled_endpoints(tmp_path, caplog):
    respx.get(f"{BASE}/account/endpoints", params={"status": "disabled"}).mock(
        return_value=httpx.Response(200, json={"endpoints": [{"endpoint": "/job/search"}, "/web/fetch"]}))
    with caplog.at_level("WARNING", logger="crust"):
        names = await check_disabled_endpoints(mk(tmp_path))
    assert names == ["/job/search", "/web/fetch"] and "/job/search" in caplog.text


@respx.mock
async def test_headers_sent(tmp_path):
    route = respx.get(f"{BASE}/account/credits").mock(return_value=httpx.Response(200, json={"credits": 1}))
    await mk(tmp_path).credits()
    h = route.calls[0].request.headers
    assert h["authorization"] == "Bearer k" and h["x-api-version"] == "2025-11-01"
