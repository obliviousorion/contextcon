"""Guided flow v2: intake, adults-only check, insurers from data, trail, diary, slider, login and memory."""
import json
import re
import sqlite3
from pathlib import Path

import pytest

from bd import guided as G, users as U
from bd.crust import Crust, Result
from bd.pipeline import Run
from bd.store import Store, h

ROOT = Path(__file__).resolve().parents[1]
A = "https://www.linkedin.com/in/atishayjain2510/"
S = "https://www.linkedin.com/in/saanvimittal/"


def replay(store, run="t"):
    return Crust(store, run, "x", mode="replay")


def person(end_year=None, city="Jaipur"):
    pd = {"crustdata_person_id": 7, "basic_profile": {"location": {"city": city}},
          "experience": {"employment_details": {"current": [{"name": "Acme", "crustdata_company_id": 9, "title": "Driver",
                                                             "start_date": "2026-10-01T00:00:00+00:00", "is_default": True}], "past": []}},
          "education": {"schools": [{"end_year": end_year}] if end_year else []}}
    return [{"match_status": "matched", "matches": [{"person_data": pd}]}]


def fake(monkeypatch, responses: dict):
    """responses: endpoint -> data (or callable(body)->data). Records every call."""
    calls = []

    def call(self, path, body=None, method="POST", cacheable=True):
        calls.append(path)
        d = responses[path](body) if callable(responses.get(path)) else responses.get(path)
        self.store.ledger_add(self.run_id, self.step, path, 0.0, 0.0, False, "ok", "test")
        return Result(True, data=d, endpoint=path, retrieved_at="2026-11-22T10:00:00+00:00")
    monkeypatch.setattr(Crust, "call", call)
    return calls


def signup(store, url=A, pin="1234"):
    res, tok = U.login(store, url, None, None, pin, True, replay(store))
    return res["user_id"], tok


def confirm_all(store, uid, age=None):
    items = [i for i in U.state(store, uid)["intake"] if not i.get("hidden")]
    dec = {}
    for i in items:
        if i["kind"] == "missing" or (i["key"] == "age_band" and age):
            dec[i["key"]] = {"action": "edit", "value": age or ("18-24" if i["key"] == "age_band" else "Pilani")}
        else:
            dec[i["key"]] = {"action": "confirm"}
    return U.confirm(store, uid, dec)


def full_run(store, uid):
    U.save_state(store, uid, answers={"dependants": ["parents"], "insurance_now": ["from_work"]})
    case = Run(store, {"id": "guided", "type": "guided_review", "user_id": uid, "as_of": "2026-11-22", "since": "2026-09-01"}).go()
    U.save_state(store, uid, last_run_id=case["run_id"])
    return case


# ---- intake and the adults-only check ---------------------------------------------
def test_age_estimate_is_guessed_with_education_basis(state):
    items = U._items(person(end_year=2027)[0]["matches"][0]["person_data"], Result(True, retrieved_at="t"))
    age = next(i for i in items if i["key"] == "age_band")
    assert age["kind"] == "guessed" and age["value"] == "18-24" and "education.schools[0].end_year = 2027" in age["basis"]


def test_age_estimate_never_used_for_adults_only_check(state, monkeypatch):
    # an estimate that says "under-18" must not refuse anyone; only the CONFIRMED age decides
    fake(monkeypatch, {"/person/enrich": person(end_year=2034)})
    s = Store()
    uid, _ = signup(s)
    est = next(i for i in U.state(s, uid)["intake"] if i["key"] == "age_band")
    assert est["kind"] == "guessed" and est["value"] == "under-18"
    assert confirm_all(s, uid, age="25-34")["stage"] == "questions"          # edited: adult, not refused
    assert U.state(s, uid)["confirmed"]["age_band"] == {"value": "25-34", "label": "told", "source": None, "edited_from": "under-18"}


def test_confirmed_under_18_is_refused_even_if_estimate_was_adult(state, monkeypatch):
    fake(monkeypatch, {"/person/enrich": person(end_year=2020)})
    s = Store()
    uid, _ = signup(s)
    assert next(i for i in U.state(s, uid)["intake"] if i["key"] == "age_band")["value"] != "under-18"
    assert confirm_all(s, uid, age="under-18")["stage"] == "refused"


def test_confirmed_guess_becomes_told(state, monkeypatch):
    fake(monkeypatch, {"/person/enrich": person(end_year=2027)})
    s = Store()
    uid, _ = signup(s)
    confirm_all(s, uid)
    assert U.state(s, uid)["confirmed"]["age_band"]["label"] == "told"
    assert U.state(s, uid)["confirmed"]["employer"]["label"] == "checked"


def test_redacted_or_missing_record_asks_plain_questions(state, monkeypatch):
    fake(monkeypatch, {"/person/enrich": [{"match_status": "redacted", "matches": []}]})
    s = Store()
    uid, _ = signup(s)
    assert all(i["kind"] == "missing" for i in U.state(s, uid)["intake"])


def test_ambiguous_name_match_falls_back_to_questions(state, monkeypatch):
    calls = fake(monkeypatch, {"/person/search": {"profiles": [{"crustdata_person_id": 1}, {"crustdata_person_id": 2}], "total_count": 2}})
    s = Store()
    res, _ = U.login(s, None, "Atishay Jain", "Amazon", "1234", True, replay(s))
    items = U.state(s, res["user_id"])["intake"]
    assert all(i["kind"] == "missing" for i in items) and "matched 2 people" in items[0]["basis"]
    assert calls == ["/person/search"]          # never enriched either lookalike


# ---- allowlist, PIN, sessions, memory ----------------------------------------------
def test_link_not_on_allowlist_makes_no_call(state, monkeypatch):
    calls = fake(monkeypatch, {})
    s = Store()
    for kw in ({"link": "https://www.linkedin.com/in/someone-else/"}, {"link": "https://x.com/atishay"},
               {"name": "Some One", "company": "Amazon"}):
        with pytest.raises(U.LoginError) as e:
            U.login(s, kw.get("link"), kw.get("name"), kw.get("company"), "1234", True, replay(s))
        assert e.value.code == 403 and "Nothing was looked up" in e.value.msg
    assert calls == [] and not s.q("SELECT * FROM ledger") and not s.q("SELECT * FROM users")


def test_wrong_pin_is_refused_and_reveals_nothing(state):
    s = Store()
    signup(s, A, "1234")
    with pytest.raises(U.LoginError) as wrong:
        U.login(s, A, None, None, "9999", True, replay(s))
    with pytest.raises(U.LoginError) as unknown:          # an allowlisted profile with no account, no consent
        U.login(s, S, None, None, "9999", False, replay(s))
    assert wrong.value.code == unknown.value.code == 401 and wrong.value.msg == unknown.value.msg
    assert "Atishay" not in wrong.value.msg and "exist" not in wrong.value.msg.lower()
    row = s.q("SELECT pin_hash, pin_salt FROM users")[0]
    assert "1234" not in row["pin_hash"] and len(row["pin_hash"]) == 64


def test_lockout_after_repeated_wrong_pins(state):
    s = Store()
    signup(s, A, "1234")
    for _ in range(5):
        with pytest.raises(U.LoginError):
            U.login(s, A, None, None, "0000", False, replay(s))
    with pytest.raises(U.LoginError):                      # even the right PIN is refused while locked
        U.login(s, A, None, None, "1234", False, replay(s))


def test_details_survive_restart_and_returning_login_makes_zero_calls(state):
    s = Store()
    uid, _ = signup(s)
    confirm_all(s, uid)
    full_run(s, uid)
    before = G.dashboard(s, uid)
    s.db.close()
    s2 = Store()                                              # a new process opening the same file
    n_ledger = len(s2.q("SELECT * FROM ledger"))
    res, tok = U.login(s2, A, None, None, "1234", False, replay(s2))
    assert res == {"user_id": uid, "returning": True, "stage": "dashboard"}
    assert len(s2.q("SELECT * FROM ledger")) == n_ledger       # zero Crustdata calls on return
    after = G.dashboard(s2, uid)
    for k in ("profile", "gaps", "trail", "diary"):
        assert after[k] == before[k]
    assert U.session_user(s2, tok) == uid


def test_forget_me_removes_every_row_for_the_user(state):
    s = Store()
    uid, tok = signup(s)
    confirm_all(s, uid)
    case = full_run(s, uid)
    G.choose(s, uid, G.dashboard(s, uid)["next_step"]["choices"][0]["company_id"])
    out = U.forget(s, uid)
    assert out["deleted"]["users"] == 1 and out["deleted"]["persona_beliefs"] > 0
    db = sqlite3.connect(s.path)
    for (t,) in db.execute("SELECT name FROM sqlite_master WHERE type='table'"):
        for row in db.execute(f"SELECT * FROM {t}"):
            text = json.dumps(row, default=str)
            assert uid not in text and case["run_id"] not in text and "atishayjain2510" not in text, (t, text[:200])
    assert U.session_user(s, tok) is None


# ---- insurers, trail ---------------------------------------------------------------
def test_insurers_come_from_data_and_are_not_ranked(state):
    s = Store()
    uid, _ = signup(s)
    confirm_all(s, uid)
    case = full_run(s, uid)
    items = case["insurers"]["items"]
    assert [i["name"] for i in items] == sorted((i["name"] for i in items), key=str.lower)   # by name, never by size
    assert all(i["claims"]["cannot_verify"] for i in items)
    assert all(f["source"]["field_path"] and f["source"]["retrieved_at"] for i in items for f in i["facts"])
    assert "not a measure" in case["insurers"]["note"] or "say nothing about how well" in case["insurers"]["note"]


def test_insurer_lookup_with_no_result_shows_cannot_verify_in_trail(state, monkeypatch):
    fake(monkeypatch, {"/person/enrich": person(end_year=2027), "/company/search": {"companies": [], "total_count": 0},
                       "/company/enrich": [], "/job/search": {"job_listings": [], "total_count": 0}})
    s = Store()
    uid, _ = signup(s)
    confirm_all(s, uid)
    case = full_run(s, uid)
    t = next(x for x in case["trail"] if x["key"] == "insurers")
    assert t["status"] == "searched, cannot verify" and "no insurer" in t["note"]


def test_no_insurer_name_is_hard_coded():
    names = ["Star Health", "Niva Bupa", "Care Health", "Aditya Birla", "Cigna", "ManipalCigna", "HDFC ERGO", "Apollo Munich"]
    files = [ROOT / "rules.yaml", ROOT / "config.yaml", *(ROOT / "bd").glob("*.py"), *(ROOT / "web" / "src").rglob("*.ts*")]
    for f in files:
        text = f.read_text()
        for n in names:
            assert n.lower() not in text.lower(), f"{n} hard-coded in {f}"


def test_trail_never_marks_a_step_done_without_a_call(state):
    s = Store()
    uid, _ = signup(s)
    confirm_all(s, uid)
    case = full_run(s, uid)
    for t in case["trail"]:
        if t["mode"] == "no call" and t["key"] != "gaps":
            assert t["status"] == "skipped"
        if t["status"] == "found":
            assert t["mode"] in ("live", "replay") and t["pointers"]


# ---- diary and slider ---------------------------------------------------------------
def test_diary_only_about_the_persona_or_big_enough_groups(state):
    s = Store()
    uid, _ = signup(s)
    confirm_all(s, uid)
    full_run(s, uid)
    from bd.beliefs import _version
    _version(s, "company:6034577", "headcount", "Staff profiles at Tiny", None, 3, "2026-11-20", [], True)   # too small
    d = G.diary(s, uid)
    assert d and all(e["subject"] == "You" or e["subject"].endswith("(group)") for e in d)
    assert not any("Tiny" in e["subject"] for e in d)
    raw = json.dumps(d)
    assert "first_name" not in raw and "last_name" not in raw


def test_slider_returns_the_belief_held_on_a_past_date(state, monkeypatch):
    s = Store()
    U.ensure(s)
    ts = iter(["2026-10-01T09:00:00+00:00", "2026-11-15T09:00:00+00:00"])  # one clock read per record_beliefs call
    monkeypatch.setattr(G, "now", lambda: next(ts))
    f = lambda city: [{"fact_id": "city", "statement": f"Your city: {city}", "value": city, "label": "told", "source": None}]
    G.record_beliefs(s, "p1", f("Pilani"), "r1", [], "choose_insurer")
    G.record_beliefs(s, "p1", f("Jaipur"), "r2", [{"rule_id": "R-GAP-1"}], "choose_insurer")
    assert G.facts_as_of(s, "p1", "2026-10-20")[0]["value"] == "Pilani"
    assert G.facts_as_of(s, "p1", "2026-11-20")[0]["value"] == "Jaipur"
    assert G.facts_as_of(s, "p1", "2026-09-01") == []
    entry = [e for e in G.diary(s, "p1") if e["new"] == "Your city: Jaipur"][0]
    assert entry["previous"] == "Your city: Pilani" and entry["gap_changed"] is True
