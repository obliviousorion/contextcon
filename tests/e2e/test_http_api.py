"""E2E: the local HTTP wrapper the web UI calls. Replay mode, 0 credits."""
import json

import pytest
from starlette.testclient import TestClient

TOKEN = "test-token"


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("MODE", "replay")
    monkeypatch.setenv("ASOF_STATE_DIR", str(tmp_path))
    monkeypatch.setenv("ASOF_TODAY", "2026-11-22")
    from backend.pipeline.session import set_session
    set_session(None)  # the pipeline keeps one session per process; start each test on its own state dir
    from backend.http_api import build_app
    yield TestClient(build_app(TOKEN))
    set_session(None)


def test_clear_returns_cited_case_file_with_cost(client):
    r = client.get("/api/casefile", params={"tool": "clear", "domain": "delhivery.com"})
    assert r.status_code == 200, r.text
    cf = r.json()["caseFile"]
    lines = cf["attestation"]["lines"]
    assert [l["field"] for l in lines] == ["existence", "listing", "headcount", "revenue_band", "domains"]
    assert all(l["status"] == "attested" and l["evidence_ids"] for l in lines)
    assert cf["cost"]["recorded_credits"] == 2.2
    assert "was true on" not in r.text


def test_dispute_moves_the_date(client):
    r = client.get("/api/casefile", params={"tool": "dispute", "domain": "tciexpress.in", "as_of": "2026-10-15"})
    hc = [l for l in r.json()["caseFile"]["attestation"]["lines"] if l["field"] == "headcount"][0]
    assert hc["refusal_code"] == "STALE_DATA" and hc["gap_days"] == 38


def test_name_is_refused_not_guessed(client):
    for tool in ("resolve", "clear"):
        r = client.get("/api/casefile", params={"tool": tool, "domain": "Shree Balaji Logistics"})
        res = r.json()["resolve"]
        assert res["status"] == "cannot_resolve" and len(res["candidates"]) == 25


def test_bad_input_is_a_clean_400(client):
    assert client.get("/api/casefile", params={"tool": "clear"}).status_code == 400
    assert client.get("/api/casefile", params={"tool": "dispute", "domain": "x.com", "as_of": "nope"}).status_code == 400
    assert client.get("/api/casefile", params={"tool": "bogus", "domain": "x.com"}).status_code == 400


def test_approval_needs_the_token_and_issue_sends_once(client, tmp_path):
    cf_id = client.get("/api/casefile", params={"tool": "clear", "domain": "delhivery.com"}).json()["caseFile"]["id"]
    assert client.post("/api/issue", json={"id": cf_id}).json()["status"] == "held_for_approval"
    assert client.post("/api/approve", json={"id": cf_id}).status_code == 403
    assert client.post("/api/approve", json={"id": cf_id}, headers={"x-asof-approval-token": "wrong"}).status_code == 403
    assert not (tmp_path / "sandbox_outbox.jsonl").exists()
    ok = client.post("/api/approve", json={"id": cf_id}, headers={"x-asof-approval-token": TOKEN})
    assert ok.status_code == 200 and ok.json()["approved_by"] == "ui"
    assert client.post("/api/approve", json={"id": cf_id}, headers={"x-asof-approval-token": TOKEN}).status_code == 409
    for _ in range(2):
        assert client.post("/api/issue", json={"id": cf_id}).json()["status"] == "done"
    assert len((tmp_path / "sandbox_outbox.jsonl").read_text().splitlines()) == 1


def test_approve_disabled_without_a_server_token(tmp_path, monkeypatch):
    monkeypatch.setenv("ASOF_STATE_DIR", str(tmp_path))
    from backend.http_api import build_app
    c = TestClient(build_app(None))
    assert c.post("/api/approve", json={"id": "CF-x"}, headers={"x-asof-approval-token": ""}).status_code == 403


def test_cost_view(client):
    client.get("/api/casefile", params={"tool": "clear", "domain": "delhivery.com"})
    assert "62.12" in json.dumps(client.get("/api/cost").json())


def test_health_attest_observe(client):
    assert client.get("/api/health").json()["mode"] == "replay"
    r = client.get("/api/attest", params={"domain": "delhivery.com", "field": "headcount", "as_of": "2024-07-15"}).json()
    assert r["line"]["value"] == 26656 and r["line"]["point_date"] == "2024-07-15"
    o = client.get("/api/observe", params={"domain": "tciexpress.in", "field": "headcount",
                                           "d1": "2020-01-01", "d2": "2026-09-01"}).json()["lines"]
    assert [x["value"] for x in o] == [418, 1715]
    assert client.get("/api/attest", params={"domain": "delhivery.com", "field": "headcount"}).status_code == 400


def test_audit_growth_claim_cannot_verify(client):
    r = client.post("/api/audit", json={"domain": "tciexpress.in",
                                       "claims": [{"id": "k1", "field": "headcount_growth", "text": "grew 4x since 2019"}]})
    assert r.status_code == 200, r.text
    assert r.json()["report"]["verdicts"][0]["verdict"] == "cannot_verify"
    assert client.post("/api/audit", json={"domain": "tciexpress.in", "claims": []}).status_code == 400


def test_file_detail_and_watch_flow_marks_stale(client):
    cf_id = client.get("/api/casefile", params={"tool": "clear", "domain": "delhivery.com"}).json()["caseFile"]["id"]
    assert client.get(f"/api/files/{cf_id}").json()["artifact"]["id"] == cf_id
    assert client.get("/api/files/CF-nope").status_code == 400
    w = client.post("/api/watch", json={"domain": "delhivery.com"}).json()
    key = w.get("watch_id_handle") or w["key"]
    assert w["status"] == "held_for_approval"
    assert client.post("/api/approve", json={"id": key}, headers={"x-asof-approval-token": TOKEN}).status_code == 200
    assert client.post("/api/issue", json={"id": key}).json()["status"] == "created"
    t = client.post("/api/watch_test", json={"id": key}).json()
    assert t["status"] == "alert" and f"{cf_id}#headcount" in t["stale_line_ids"]
    assert client.post("/api/watch_test", json={"id": key}).json()["status"] == "no_op"
    lines = client.get(f"/api/files/{cf_id}").json()["artifact"]["attestation"]["lines"]
    assert [l for l in lines if l["field"] == "headcount"][0].get("stale") is True


def test_evidence_request_is_not_a_negative_finding(client):
    r = client.post("/api/evidence_request", json={"target": "shreebalajigrp.com", "items": ["GSTIN"]}).json()
    assert r["request"]["note"] == "Not a negative finding." and r["request"]["status"] == "draft"
