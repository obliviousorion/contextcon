"""Unit tests: job-change rule, date tolerance, label rules, gaps, group suppression, pointers, sign-up."""
import pytest
import yaml

from bd import facts as F
from bd import rules_engine as R
from bd.config import load_rules
from bd.store import Store


def job(cid, s, e=None, default=False, name="X"):
    return {"name": name, "crustdata_company_id": cid, "title": "t", "start_date": s, "end_date": e,
            "is_default": default, "employment_type": "Full-time"}


def person(cur, past):
    return {"crustdata_person_id": 1, "experience": {"employment_details": {"current": cur, "past": past}}}


def test_new_employer_is_job_change():
    a = R.job_change(person([job(2, "2026-10-01", default=True)], [job(1, "2024-01-01", "2026-09-01")]),
                     "2026-09-01", "2026-11-22", "t")
    assert a["status"] == "job_change" and a["cover_end_date"] == "2026-09-01" and a["change_date"] == "2026-10-01"
    assert a["deadline_passed"] is True  # 2026-10-01 < 2026-11-22


def test_promotion_same_company_is_not_job_change():
    a = R.job_change(person([job(1, "2026-10-01", default=True)], [job(1, "2024-01-01", "2026-10-01")]),
                     "2026-09-01", "2026-11-22", "t")
    assert a["status"] == "same_company"


def test_several_current_jobs_without_default_is_cannot_verify():
    a = R.job_change(person([job(1, "2026-10-01"), job(2, "2026-10-01")], []), "2026-09-01", "2026-11-22", "t")
    assert a["status"] == "cannot_verify"


def test_default_job_is_main_job():
    a = R.job_change(person([job(9, "2026-01-01"), job(2, "2026-10-01", default=True)],
                            [job(1, "2024-01-01", "2026-09-01")]), "2026-09-01", "2026-11-22", "t")
    assert a["status"] == "job_change" and "-> 2" in a["explanation"]


def test_first_of_month_tolerance():
    # started 2026-08-01: one month before the window, inside tolerance
    a = R.job_change(person([job(2, "2026-08-01", default=True)], [job(1, "2024-01-01", "2026-08-01")]),
                     "2026-09-01", "2026-11-22", "t")
    assert a["status"] == "job_change"
    b = R.job_change(person([job(2, "2026-06-01", default=True)], [job(1, "2024-01-01", "2026-06-01")]),
                     "2026-09-01", "2026-11-22", "t")
    assert b["status"] == "no_change_on_record"


def test_guessed_facts_never_drive_gaps():
    facts = [{"fact_id": "cover_held", "label": "guessed", "value": []}]
    assert R.gaps(facts, None) == []
    told = [{"fact_id": "cover_held", "label": "told", "value": []}]
    assert [g["rule_id"] for g in R.gaps(told, None)] == ["R-GAP-1"]


def test_unresolved_pointer_is_cannot_verify():
    f = F.checked("x", "X: {v}", {"a": {}}, "a.b[0].c", "rec", "1", "t")
    assert f["cannot_verify"] and f["value"] is None
    g = F.checked("x", "X: {v}", {"a": {"b": [{"c": 5}]}}, "a.b[0].c", "rec", "1", "t")
    assert g["value"] == 5 and g["statement"] == "X: 5"


def test_dedupe_on_exact_identifier_only(state):
    s = Store()
    a = F.sign_up(s, {"profile_url": "https://www.linkedin.com/in/abc/", "consent": True})
    b = F.sign_up(s, {"profile_url": "HTTPS://linkedin.com/in/ABC?utm=x", "consent": True})
    c = F.sign_up(s, {"profile_url": "https://www.linkedin.com/in/abc-1/", "consent": True})  # lookalike
    assert a["persona_id"] == b["persona_id"] and b["signups"] == 2
    assert c["persona_id"] != a["persona_id"]


def test_refusals(state):
    s = Store()
    for p, code in [({"consent": False, "profile_url": "u"}, "NO_CONSENT"),
                    ({"consent": True, "name": "A B"}, "NEED_PROFILE_LINK"),
                    ({"consent": True, "profile_url": "u", "answers": {"age_band": "under-18"}}, "UNDER_18")]:
        with pytest.raises(F.Refused) as e:
            F.sign_up(s, p)
        assert e.value.code == code


def test_forget_deletes_facts(state):
    s = Store()
    p = F.sign_up(s, {"profile_url": "https://x.test/in/p", "consent": True})
    s.x("INSERT INTO facts VALUES (?,?,?,?,?,?,?,?)", p["persona_id"], "city", "City", '"Jaipur"', "told", "{}", None, None)
    r = F.forget(s, p["persona_id"])
    assert r["deleted_facts"] == 1 and not s.q("SELECT * FROM facts")


def test_insurer_needs_two_verified_figures():
    ins = [{"insurer": "A", "figures": [{"metric": "claim_settlement_ratio", "value": 90},
                                        {"metric": "complaints_per_10k_claims", "value": 10}]},
           {"insurer": "B", "figures": [{"metric": "claim_settlement_ratio", "value": 95},
                                        {"metric": "complaints_per_10k_claims", "cannot_verify": True, "missing": "x"}]},
           {"insurer": "C", "figures": [{"metric": "claim_settlement_ratio", "value": 80},
                                        {"metric": "complaints_per_10k_claims", "value": 50}]}]
    out = R.rank_insurers(ins)
    assert [i["insurer"] for i in out if i["rank"]] == ["A", "C"]
    assert next(i for i in out if i["insurer"] == "B")["rank"] is None


def test_live_fix_rule_change_in_yaml_only(tmp_path, monkeypatch):
    """Live-fix drill: change one number in rules.yaml; the result changes with no code change."""
    facts = [{"fact_id": "monthly_budget_inr", "label": "told", "value": 600},
             {"fact_id": "cover_held", "label": "told", "value": ["personal_health"]}]
    assert R.gaps(facts, None) == []
    rules = load_rules()
    next(g for g in rules["gaps"] if g["id"] == "R-GAP-6")["when"]["budget_below"] = 1000
    p = tmp_path / "rules.yaml"; p.write_text(yaml.safe_dump(rules))
    monkeypatch.setenv("BD_RULES", str(p))
    assert [g["rule_id"] for g in R.gaps(facts, None)] == ["R-GAP-6"]


def test_small_group_belief_is_suppressed(state, monkeypatch):
    from bd import beliefs as B
    monkeypatch.setattr(B, "measure", lambda c, g, end, days: {"staff_now": 3, "joiners": 2, "contract_joiners": 0,
                                                                "leavers": 1, "leavers_checked": 1, "leaver_candidates": 1})
    monkeypatch.setattr(B, "_timeline", lambda c, g, r: [])
    out = B.beliefs_for(Store(), None, {"company_id": 1, "city": "X"})
    assert out["beliefs"] and all(b["suppressed"] and b["value"] is None and "too small" in b["reason"] for b in out["beliefs"])


def test_new_evidence_closes_old_belief_version(state):
    from bd import beliefs as B
    s = Store()
    B._version(s, "g", "joiners", "J", 20, 100, "2026-10-01", [], False)
    B._version(s, "g", "joiners", "J", 9, 100, "2026-11-22", [], False)
    B._version(s, "g", "joiners", "J", 9, 100, "2026-11-22", [], False)  # restart: idempotent
    rows = [dict(r) for r in s.q("SELECT version, value, valid_from, valid_to FROM beliefs ORDER BY version")]
    assert rows == [{"version": 1, "value": 20, "valid_from": "2026-10-01", "valid_to": "2026-11-22"},
                    {"version": 2, "value": 9, "valid_from": "2026-11-22", "valid_to": None}]
