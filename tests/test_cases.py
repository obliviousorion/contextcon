"""The Open-track test cases and hard cases, run end to end in replay against recorded fixtures."""
import json
from pathlib import Path

import yaml

from bd.pipeline import Run
from bd.store import Store

REQ = Path(__file__).resolve().parents[1] / "requests"


def run(name):
    return Run(Store(), json.loads((REQ / f"{name}.json").read_text())).go()


def test_T1_new_employer_after_sep_2026(state):
    c = run("T1_job_change")
    a = c["alarm"]
    assert a["status"] == "job_change" and a["change_date"] == "2026-10-01" and a["cover_end_date"] == "2026-09-01"
    assert a["old_employer"] == "Delhivery" and a["new_employer"] == "TCI Express Ltd."
    assert all(s["field_path"] for s in a["sources"])
    assert [x["action"] for x in c["actions"]] == ["conversion_request"]
    assert c["actions"][0]["status"] == "awaiting_approval"


def test_T1b_same_company_promotion_no_alarm(state):
    c = run("T1b_promotion")
    assert c["alarm"]["status"] == "same_company" and c["actions"] == []


def test_T2_peer_share(state):
    pb = run("T2_peer_share")["peer_benchmark"]
    assert pb["total"] == 3434
    by = {p["phrase"]: p["count"] for p in pb["phrases"]}
    assert by["health insurance"] == 114 and by["medical insurance"] == 119 and by["ESIC"] == 17
    assert pb["any_cover"] == {"count": 246, "share": 0.0716}
    assert pb["filter"]["conditions"][2] == {"field": "metadata.date_added", "type": "=>", "value": "2026-09-01"}
    assert pb["source"]["retrieved_at"] and "not mentioned" in pb["note"]
    for s in pb["samples"]:  # every quoted passage really is in the record, at its char range
        assert s["phrase"].lower() in s["passage"].lower() and s["url"]


def test_T3_no_public_record_is_cannot_verify(state):
    c = run("T3_no_record")
    assert any("Employer" in x["statement"] for x in c["cannot_verify"])
    assert any("employer" in q["question"].lower() for q in c["questions"])
    assert all(f["label"] == "told" for f in c["facts"])
    assert c["cost"]["credits"] == 0


def test_duplicate_signup_is_one_persona_and_one_action(state):
    a = run("L1_persona_a_review")
    b = run("H1_duplicate_signup")
    assert a["persona"]["persona_id"] == b["persona"]["persona_id"] and b["persona"]["signups"] == 2
    assert len(b["actions"]) == 1 and b["actions"][0]["key"] == a["actions"][0]["key"]


def test_lookalike_name_only_is_refused(state):
    c = run("H2_lookalike_name_only")
    assert c["status"] == "refused" and c["refusal"]["code"] == "NEED_PROFILE_LINK"


def test_under_18_stops(state):
    assert run("H3_under_18")["refusal"]["code"] == "UNDER_18"


def test_persona_without_change_cannot_verify_absence(state):
    c = run("L2_persona_b_alarm")
    assert c["alarm"]["status"] == "no_change_on_record"
    assert "cannot verify" in c["alarm"]["explanation"]


def test_restart_skips_finished_steps(state):
    run("T2_peer_share")
    again = run("T2_peer_share")
    assert "peer_benchmark" in again["skipped_steps"] and again["cost"]["credits"] == 0


def test_requirement_change_drill_config_only(state, tmp_path, monkeypatch):
    """Add an output field and lower the cost cap through config.yaml only."""
    cfg = yaml.safe_load((REQ.parent / "config.yaml").read_text())
    cfg["output"]["fields"] = [f for f in cfg["output"]["fields"] if f != "questions"]
    cfg["limits"]["credit_cap_per_run"] = 0.01
    p = tmp_path / "config.yaml"; p.write_text(yaml.safe_dump(cfg))
    monkeypatch.setenv("BD_CONFIG", str(p))
    c = run("T3_no_record")
    assert "questions" not in c and c["cost"]["cap"] == 0.01


def test_budget_cap_holds_before_a_paid_call(state, monkeypatch):
    """A paid call that would cross the cap is never sent: kind=held, logged, no network."""
    from bd.crust import Crust
    st = Store()
    c = Crust(st, "cap-test", "s", mode="record", credit_cap=0.5)
    r = c.person_enrich("https://x.test/in/uncached")
    assert r.kind == "held" and "credit cap" in r.reason
    assert st.q("SELECT status FROM ledger WHERE run_id='cap-test'")[0]["status"] == "held"


def test_E1_employer_view_replay(state):
    c = run("E1_employer_package")
    assert c["status"] == "finished" and [p["role"] for p in c["package"]] == ["drivers", "warehouse staff", "office staff"]
    roles = {r["role"]: r for r in c["peer_benchmark"]["by_role"]}
    assert roles["drivers"]["total"] == 16 and roles["warehouse staff"]["with_cover"] == 5
    b = {(x["belief_key"], x["version"]): x for x in c["workplace"]["beliefs"]}
    assert b[("joiners", 1)]["value"] == 20 and b[("joiners", 1)]["valid_to"] == "2026-11-22"
    assert b[("joiners", 2)]["value"] == 9 and b[("joiners", 2)]["valid_to"] is None
    assert "checked 10 of" in b[("leavers", 1)]["statement"]
