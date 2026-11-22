"""Live mode behind the gate: replay first, a spend only after confirm, cached after, capped.
The network is mocked with respx, so these tests spend nothing."""
import copy
import json
from pathlib import Path

import httpx
import pytest
import respx
from starlette.testclient import TestClient

ROOT = Path(__file__).resolve().parents[2]
CACHE = ROOT / "fixtures" / "live_check" / "cache"
NEW_DOMAIN, NEW_ID = "newco-logistics.example", 99000001


def _recorded(path: str, body_key: str, value) -> dict:
    for f in CACHE.glob("*.json"):
        d = json.loads(f.read_text())
        r = d.get("request") or {}
        if r.get("path") == path and (r.get("body") or {}).get(body_key) == value:
            return d
    raise AssertionError(f"no recorded {path} for {value}")


def _fake_responses():
    ident = copy.deepcopy(_recorded("/company/identify", "domains", ["delhivery.com"])["response"])
    enr = copy.deepcopy(_recorded("/company/enrich", "crustdata_company_ids", [5798])["response"])
    for item in ident:
        for m in item.get("matches") or []:
            cd = m["company_data"]
            cd.setdefault("basic_info", {})
            cd["crustdata_company_id"] = NEW_ID
            cd["basic_info"]["primary_domain"] = NEW_DOMAIN
            cd["basic_info"]["all_domains"] = [NEW_DOMAIN]
            cd["basic_info"]["name"] = "NewCo Logistics"
    for item in enr:
        for m in item.get("matches") or []:
            cd = m["company_data"]
            cd["crustdata_company_id"] = NEW_ID
            cd["basic_info"]["primary_domain"] = NEW_DOMAIN
            cd["basic_info"]["all_domains"] = [NEW_DOMAIN]
            cd["basic_info"]["name"] = "NewCo Logistics"
    return ident, enr


@pytest.fixture
def live_client(tmp_path, monkeypatch):
    monkeypatch.setenv("ASOF_STATE_DIR", str(tmp_path))
    monkeypatch.setenv("ASOF_TODAY", "2026-11-22")
    monkeypatch.setenv("CRUST_KEY", "test-key-not-real")
    from backend.http_api import build_app
    from backend.live_gate import LiveGate
    from backend.pipeline.session import set_session
    set_session(None)
    gate = LiveGate(live=True, session_cap=5.0)
    yield TestClient(build_app("tok", gate)), gate
    set_session(None)


def test_stored_company_is_free_even_when_live(live_client):
    c, gate = live_client
    with respx.mock(assert_all_called=False) as net:
        r = c.get("/api/casefile", params={"tool": "clear", "domain": "delhivery.com"}).json()
        assert net.calls.call_count == 0
    assert r["caseFile"]["cost"]["credits"] == 0.0 and gate.spent == 0.0


def test_unknown_company_asks_first_then_spends_once_then_is_cached(live_client):
    c, gate = live_client
    ident, enr = _fake_responses()
    with respx.mock(assert_all_called=False) as net:
        id_route = net.post("https://api.crustdata.com/company/identify").mock(
            return_value=httpx.Response(200, json=ident))
        en_route = net.post("https://api.crustdata.com/company/enrich").mock(
            return_value=httpx.Response(200, json=enr))
        ask = c.get("/api/casefile", params={"tool": "clear", "domain": NEW_DOMAIN}).json()
        assert ask["needs_confirmation"] is True and ask["estimate_credits"] == 2.2
        assert ask["estimate_inr"] == 62.12 and net.calls.call_count == 0  # nothing spent without confirm

        got = c.get("/api/casefile", params={"tool": "clear", "domain": NEW_DOMAIN, "confirm": "1"}).json()
        cf = got["caseFile"]
        assert cf["resolve"]["status"] == "resolved"
        assert cf["resolve"]["entity"]["crustdata_company_id"] == NEW_ID
        assert id_route.call_count == 1 and en_route.call_count == 1
        assert 0 < gate.spent <= 2.2 + 1e-9

        again = c.get("/api/casefile", params={"tool": "clear", "domain": NEW_DOMAIN}).json()
        assert "caseFile" in again and "needs_confirmation" not in again
        assert id_route.call_count == 1 and en_route.call_count == 1  # served from the live cache
    assert c.get("/api/health").json()["session_spent_credits"] == round(gate.spent, 4)


def test_session_cap_blocks_before_any_call(live_client):
    c, gate = live_client
    gate.spent = 4.0  # cap 5.0, estimate 2.2
    with respx.mock(assert_all_called=False) as net:
        r = c.get("/api/casefile", params={"tool": "clear", "domain": NEW_DOMAIN, "confirm": "1"})
        assert r.status_code == 402 and r.json()["blocked"] is True
        assert net.calls.call_count == 0


def test_replay_only_server_never_offers_a_spend(tmp_path, monkeypatch):
    monkeypatch.setenv("ASOF_STATE_DIR", str(tmp_path))
    from backend.http_api import build_app
    from backend.pipeline.session import set_session
    set_session(None)
    c = TestClient(build_app("tok"))
    with respx.mock(assert_all_called=False) as net:
        r = c.get("/api/casefile", params={"tool": "clear", "domain": NEW_DOMAIN, "confirm": "1"}).json()
        assert "needs_confirmation" not in r and net.calls.call_count == 0
    assert "replay" in json.dumps(r)
    assert c.get("/api/health").json()["mode"] == "replay"
    set_session(None)


def test_live_cache_never_writes_into_committed_fixtures(live_client, tmp_path):
    _, gate = live_client
    assert gate.cache_dir == tmp_path / "live-cache"
    assert any(gate.cache_dir.glob("*.json"))  # seeded with the recorded copies
