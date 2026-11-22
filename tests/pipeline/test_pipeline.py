import json
import time
from types import SimpleNamespace

import pytest

from backend.crust.ledger import CREDIT_TO_INR

from backend.cli import main
from backend.crust.results import CrustResult
from backend.models import ClaimInput
from backend.pipeline import (RequestError, attest, audit_claims, clear_counterparty, dispute_file, request_evidence,
                              resolve)
from backend.pipeline.session import Session, set_session


async def test_c08_name_with_25_candidates_cannot_resolve(session):
    r = await resolve(name="Shree Balaji Logistics")
    assert r.status == "cannot_resolve" and len(r.candidates) == 25
    assert "domain" in r.missing and r.entity is None


async def test_c17_alias_is_not_proof_without_identify(session):
    # delhivery.com's record lists drl.aero, but an alias is not proof: drl.aero gets its own identify
    a = await resolve(domain="delhivery.com")
    assert a.entity.crustdata_company_id == 5798 and "drl.aero" in a.entity.domains
    b = await resolve(domain="drl.aero")
    assert b.status == "cannot_resolve" and b.entity is None
    assert session.client.network_calls == 0  # replayed, never live


async def test_c17_drl_aero_identify_matches_two_companies(session):
    # live record-mode identify, 2026-11-22: drl.aero -> Delhivery (5798) AND Delhivery Robotics (15944579)
    r = await resolve(domain="drl.aero")
    assert r.status == "cannot_resolve" and r.entity is None
    assert {c.crustdata_company_id for c in r.candidates} == {5798, 15944579}
    assert "exactly one company" in r.missing
    assert session.client.network_calls == 0


class CountingClient:
    """Duck-typed client: counts identify calls; one company, two domains."""
    mode = "live"
    run_id = "x"
    cache = SimpleNamespace(dir="/nonexistent")

    def __init__(self):
        self.identify_calls = 0
        self.ledger = SimpleNamespace(entries=[])

    async def autocomplete(self, body, **kw):
        return CrustResult(ok=True, data={"suggestions": []})

    async def company_identify(self, body, **kw):
        self.identify_calls += 1
        cd = {"crustdata_company_id": 7, "basic_info": {"name": "Acme", "primary_domain": "acme.com",
                                                        "all_domains": ["acme.com", "acme.io"]}}
        return CrustResult(ok=True, data=[{"matched_on": body["domains"][0], "match_type": "domain",
                                           "matches": [{"confidence_score": 1.0, "company_data": cd}]}],
                           retrieved_at="2026-11-22T08:00:00+00:00", cache_key="k")


async def test_two_domains_one_company_charged_once():
    c = CountingClient()
    set_session(Session(client=c))
    a = await resolve(domain="acme.com")
    b = await resolve(domain="https://www.ACME.io/about")
    assert a.entity is b.entity and a.entity.crustdata_company_id == 7  # one record, two domains
    assert c.identify_calls == 2  # each new domain is identified (0.2 credits), never assumed
    again = await resolve(domain="acme.io")
    assert again.entity is a.entity and c.identify_calls == 2  # an identified domain is cached


async def test_unknown_domain_clean_cannot_resolve(session):
    r = await resolve(domain="no-such-company-xyz.com")
    assert r.status == "cannot_resolve" and r.missing and r.entity is None
    cf = await clear_counterparty("no-such-company-xyz.com")
    assert cf.resolve.status == "cannot_resolve" and cf.attestation is None
    assert cf.evidence_request and cf.evidence_request.note == "Not a negative finding."


@pytest.mark.parametrize("bad", ["", "   ", None, "!!!", "not a domain", "localhost"])
async def test_garbage_domain_clean_error(session, bad):
    with pytest.raises(RequestError):
        await clear_counterparty(bad)
    with pytest.raises(RequestError):
        await resolve(domain=bad) if bad else await resolve()


async def test_garbage_requests_clean_errors(session):
    with pytest.raises(RequestError):
        await attest("delhivery.com", "headcount", "not-a-date")
    with pytest.raises(RequestError):
        await attest("delhivery.com", "", "2024-07-15")
    with pytest.raises(RequestError):
        await audit_claims("delhivery.com", [])
    with pytest.raises(RequestError):
        await audit_claims("delhivery.com", [{"nope": 1}])
    with pytest.raises(RequestError):
        await request_evidence("", ["x"])
    with pytest.raises(RequestError):
        await request_evidence("acme.com", [])
    with pytest.raises(RequestError):
        await dispute_file("delhivery.com", "2999-01-01")


async def test_unknown_field_is_no_record_type_without_spending(session):
    ln = await attest("delhivery.com", "gstin", "2024-07-15")
    assert ln.status == "cannot_attest" and ln.refusal_code == "NO_RECORD_TYPE"


async def test_clear_counterparty_delhivery_end_to_end(session):
    t = time.time()
    cf = await clear_counterparty("delhivery.com")
    assert time.time() - t < 10
    assert cf.kind == "clearance" and cf.status == "draft" and cf.attestation
    assert [l.field for l in cf.attestation.lines] == ["existence", "listing", "headcount", "revenue_band", "domains"]
    assert cf.evidence and cf.cost is not None and cf.cost.inr >= 0
    ids = list(cf.evidence)
    assert ids == [f"E{i}" for i in range(1, len(ids) + 1)]  # globally renumbered, no gaps
    for ln in cf.attestation.lines:
        for e in ln.evidence_ids:
            assert e in cf.evidence
        if ln.status == "attested":
            assert ln.evidence_ids
    for ev in cf.evidence.values():
        assert ev.retrieved_at and ev.excerpt
    assert cf.evidence["E1"].source_endpoint == "/company/identify"
    assert len(cf.idempotency_key) == 64
    again = await clear_counterparty("delhivery.com")
    assert again.idempotency_key == cf.idempotency_key and again.id == cf.id


async def test_dispute_file_past_date(session):
    cf = await dispute_file("tciexpress.in", "2020-01-01")
    assert cf.kind == "dispute" and cf.request["as_of"] == "2020-01-01"
    assert cf.attestation.as_of.isoformat() == "2020-01-01"


async def test_small_company_gets_evidence_request(session):
    cf = await clear_counterparty("shreebalajigrp.com")
    ex = [l for l in cf.attestation.lines if l.field == "existence"][0]
    assert ex.status == "cannot_attest" and "year_founded" in (ex.missing or "")
    er = cf.evidence_request
    assert er and er.status == "draft" and er.note == "Not a negative finding."
    assert any("registration" in i for i in er.items)


async def test_request_evidence_held_and_idempotent(session):
    a = await request_evidence("acme.com", ["GSTIN", "domain"])
    b = await request_evidence("acme.com", ["domain", "GSTIN"])
    assert a.status == "draft" and a.note == "Not a negative finding." and a.idempotency_key == b.idempotency_key


async def test_audit_claims_uses_engine(session):
    rep = await audit_claims("tciexpress.in", [ClaimInput(id="k1", text="grew 4x", field="headcount_growth")])
    assert rep.verdicts[0].claim_id == "k1" and rep.verdicts[0].verdict == "cannot_verify"
    assert rep.status == "draft"


async def test_issue_is_held_without_platform_send(session, monkeypatch):
    cf = await clear_counterparty("delhivery.com")
    from backend.pipeline import api
    monkeypatch.setattr(api, "_platform", lambda: None)
    out = await api.issue(cf.id)
    assert out["status"] == "held_for_approval"


def test_cli_json_and_clean_errors(capsys, monkeypatch):
    monkeypatch.setenv("MODE", "replay")
    set_session(None)
    assert main(["resolve", "--name", "Shree Balaji Logistics"]) == 0
    out = json.loads(capsys.readouterr().out)
    assert out["status"] == "cannot_resolve" and len(out["candidates"]) == 25
    assert main(["attest", "", "headcount", "2024-01-01"]) == 2
    assert "error" in json.loads(capsys.readouterr().out)
    assert main(["attest", "delhivery.com", "headcount", "garbage"]) == 2
    assert "Traceback" not in capsys.readouterr().out
    assert main(["bogus"]) == 2


async def test_issue_held_then_approved_sends_once(session, tmp_path, monkeypatch):
    monkeypatch.setenv("ASOF_STATE_DIR", str(tmp_path / "st2"))
    monkeypatch.delenv("SANDBOX_WEBHOOK_URL", raising=False)
    plat = pytest.importorskip("backend.platform.actions")
    from backend.pipeline import api
    cf = await clear_counterparty("delhivery.com")
    held = await api.issue(cf.id)
    assert held["status"] == "held_for_approval"
    ap = await api.approve(cf.id, by="priya")
    assert ap["first_approval"] is True and ap["approved_by"] == "priya" and ap["approved_at"]
    assert (await api.show(cf.id))["approval"]["by"] == "priya"
    with pytest.raises(RequestError):  # no longer a draft: a double click is refused cleanly
        await api.approve(cf.id)
    a = await api.issue(cf.id)
    b = await api.issue(cf.id)
    assert a["status"] == b["status"] == "done"
    sent = (plat.outbox_path().read_text().splitlines())
    assert len(sent) == 1


async def test_cost_block_replay_records_what_it_cost(session):
    cf = await clear_counterparty("delhivery.com")
    c = cf.cost
    assert (c.credits, c.inr, c.calls) == (0, 0, 0)          # nothing spent this run
    assert c.cache_hits == 2                                   # identify result + enrich record
    assert c.recorded_credits == pytest.approx(2.2)            # identify 0.2 + enrich 2
    assert c.recorded_inr == pytest.approx(round(2.2 * CREDIT_TO_INR, 2))  # 2.2 credits x config rate


async def test_shared_alias_gets_evidence_request_not_a_guess(session):
    await clear_counterparty("delhivery.com")
    cf = await clear_counterparty("drl.aero")  # listed on Delhivery's record, but shared with another company
    assert cf.resolve.status == "cannot_resolve" and cf.attestation is None
    assert cf.evidence_request and cf.evidence_request.note == "Not a negative finding."
    assert cf.cost.credits == 0  # replay


async def test_rerun_resumes_with_zero_client_calls(session, tmp_path, monkeypatch):
    first = await clear_counterparty("delhivery.com")
    # fresh session, same state dir: runstate has every step, so no client call may happen
    fresh = Session(client=session.client)
    set_session(fresh)
    calls = []
    for n in ("company_identify", "company_enrich", "autocomplete"):
        monkeypatch.setattr(session.client, n, lambda *a, _n=n, **k: calls.append(_n))
    again = await clear_counterparty("delhivery.com")
    assert calls == [] and again.idempotency_key == first.idempotency_key
    assert [l.model_dump() for l in again.attestation.lines] == [l.model_dump() for l in first.attestation.lines]
    assert again.cost.recorded_credits == pytest.approx(2.2)


async def test_cap_hit_returns_budget_held_case_file(session, monkeypatch):
    from backend.platform import runstate
    monkeypatch.setattr(runstate, "limits", lambda cfg=None: (0.0, 300.0))  # cap already reached
    cf = await clear_counterparty("delhivery.com")
    assert cf.status == "draft" and cf.resolve.status == "cannot_resolve"
    assert "limit" in cf.resolve.missing
    monkeypatch.setattr(runstate, "limits", lambda cfg=None: (40.0, 300.0))
    ok = await clear_counterparty("delhivery.com")  # resumable
    assert ok.attestation is not None


async def test_cap_hit_midway_marks_lines_budget_held(session, monkeypatch):
    from backend.platform import runstate
    seen = {"n": 0}
    real = runstate.limits

    def limits(cfg=None):
        seen["n"] += 1
        return (0.0, 300.0) if seen["n"] > 3 else real()
    monkeypatch.setattr(runstate, "limits", limits)
    cf = await clear_counterparty("delhivery.com")
    codes = [l.refusal_code for l in cf.attestation.lines]
    assert "BUDGET_HELD" in codes and cf.attestation.lines[0].status == "attested"


async def test_sandbox_payload_carries_idempotency_key(session, monkeypatch):
    from backend.platform import actions
    sent = []
    monkeypatch.setattr(actions, "sandbox_send", lambda p: sent.append(p) or "outbox")
    cf = await clear_counterparty("delhivery.com")
    from backend.pipeline import api
    await api.approve(cf.id)
    await api.issue(cf.id)
    assert sent and sent[0]["idempotency_key"] == cf.idempotency_key


async def test_beat5_watch_to_stale_flow(session):
    from backend.pipeline import api
    cf = await clear_counterparty("delhivery.com")
    held = await api.watch("delhivery.com")
    key = held["key"]
    assert held["status"] == "held_for_approval"
    assert (await api.issue(key))["status"] == "held_for_approval"
    await api.approve(key, by="ops")
    made = await api.issue(key)
    assert made["status"] == "created" and made["watch_id"].startswith("w-")
    alert = await api.watch_test(made["watch_id"])
    assert alert["status"] == "alert" and alert["stale_line_ids"] == [f"{cf.id}#headcount"]
    shown = await api.show(cf.id)
    flagged = [l["field"] for l in shown["artifact"]["attestation"]["lines"] if l.get("stale")]
    assert flagged == ["headcount"] and shown["stale"][0]["snapshot"]["stale_line_ids"]
    again = await api.watch_test(made["watch_id"])
    assert again["status"] == "no_op"
    assert len((await api.show(cf.id))["stale"]) == 1


async def test_watch_test_unknown_id_clean_error(session):
    from backend.pipeline import api
    with pytest.raises(RequestError):
        await api.watch_test("w-nope")


async def test_cost_view_label(session):
    from backend.pipeline import api
    await clear_counterparty("delhivery.com")
    f = (await api.cost())["case_files"][0]
    assert f["label"] == f"\u20b90.00 spent this run (replay); \u20b9{2.2 * CREDIT_TO_INR:.2f} measured cost of the stored copies (2.2 credits)"


def test_cli_cost_note(capsys, monkeypatch):
    label = f"\u20b90.00 spent this run (replay); \u20b9{2.2 * CREDIT_TO_INR:.2f} measured cost of the stored copies (2.2 credits)"
    monkeypatch.setenv("MODE", "replay")
    set_session(None)
    assert main(["clear", "delhivery.com"]) == 0
    assert json.loads(capsys.readouterr().out)["cost_note"] == label


def test_cli_positional_name_and_audit_help(capsys, monkeypatch):
    monkeypatch.setenv("MODE", "replay")
    set_session(None)
    assert main(["resolve", "Shree Balaji Logistics"]) == 0
    assert json.loads(capsys.readouterr().out)["status"] == "cannot_resolve"
    assert main(["audit", "--help"]) == 0
    assert '"field"' in capsys.readouterr().out or "claim schema" in capsys.readouterr().out


async def test_ledger_run_id_stable_across_restart(tmp_path):
    from backend.crust.client import CrustClient
    from backend.pipeline.session import FIXTURE_CACHE

    def fresh():
        c = CrustClient(run_id="random-" + str(time.time_ns()), mode="replay", cache_dir=FIXTURE_CACHE,
                        ledger_dir=tmp_path / "ledger")
        set_session(Session(client=c))
        return c

    c1 = fresh()
    cf1 = await clear_counterparty("delhivery.com")
    path1, lines1 = c1.ledger.path, c1.ledger.path.read_text() if c1.ledger.path.exists() else ""
    c2 = fresh()  # "kill": all process state dropped, new random client run_id
    cf2 = await clear_counterparty("delhivery.com")
    assert c2.ledger.path == path1 and c2.run_id == c1.run_id and c2.run_id.startswith("cf-")
    after = path1.read_text() if path1.exists() else ""
    assert after == lines1  # resumed run added nothing: no double count
    assert cf2.cost.recorded_credits == cf1.cost.recorded_credits
    c3 = fresh()
    await attest("delhivery.com", "headcount", "2024-07-15")
    assert c3.run_id.startswith("rq-")


def test_recorded_unit_credits_from_ledgers(tmp_path):
    from backend.pipeline.session import cfg_get, recorded_unit_credits
    assert recorded_unit_credits() == {"identify": 0.2, "enrich": 2.0}
    with pytest.raises(RuntimeError, match="no recorded price"):
        recorded_unit_credits(tmp_path)
    with pytest.raises(KeyError, match="limits.nope"):
        cfg_get({"limits": {}}, "limits", "nope")
