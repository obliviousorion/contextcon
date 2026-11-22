"""The guided review: You -> Your employer -> People like you -> Insurers -> Gaps.

Each step records a trail entry (what was searched, source, records, credits, status, live or replay with the
recorded date, and the source pointers). A step that made no call is never shown as found.
Beliefs about the person are versioned (valid_from / valid_to); the diary and the date slider read only that
store and the group belief store. No new calls, no model-written text.
"""
from __future__ import annotations

import json
from datetime import date
from typing import Any

from . import actions, peers, rules_engine as R
from .beliefs import _version
from .config import load_config, load_rules
from .crust import Crust, Result
from .facts import person_entry
from .insurers import find as find_insurers
from .store import Store, h, now
from . import users as U


class Tracked(Crust):
    """A Crust client that remembers every call it made, for the trail."""
    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        self.calls: list[Result] = []

    def call(self, path, body=None, method="POST", cacheable=True):
        r = super().call(path, body, method, cacheable)
        self.calls.append(r)
        return r


def _records(r: Result) -> int:
    d = r.data
    if isinstance(d, list):
        return sum(len(i.get("matches") or []) for i in d if isinstance(i, dict))
    if isinstance(d, dict):
        for k in ("companies", "profiles", "job_listings"):
            if isinstance(d.get(k), list) and d.get(k):
                return len(d[k])
        if d.get("total_count") is not None:
            return int(d["total_count"])
    return 0


def trail_entry(key: str, title: str, searched: str, source: str, calls: list[Result], found: bool,
                pointers: list[dict], records: int | None = None, note: str = "") -> dict:
    if not calls:
        return {"key": key, "title": title, "searched": searched, "source": source, "records": None, "credits": 0,
                "status": "skipped", "mode": "no call", "recorded_at": None, "pointers": [], "note": note or "no call was made"}
    if all(c.kind in ("replay_miss", "held") for c in calls):
        return {"key": key, "title": title, "searched": searched, "source": source, "records": None, "credits": 0,
                "status": "skipped", "mode": "replay", "recorded_at": None, "pointers": [],
                "note": note or ("nothing recorded to replay; switch to Live to look it up" if calls[0].kind == "replay_miss"
                                 else calls[0].reason)}
    live = [c for c in calls if not c.cache_hit and c.kind not in ("replay_miss", "held")]
    misses = [c for c in calls if c.kind in ("replay_miss", "held", "error")]
    recorded = sorted({(c.retrieved_at or "")[:19] for c in calls if c.cache_hit and c.retrieved_at})
    status = "found" if found and not (misses and not live and not any(c.ok for c in calls)) else "searched, cannot verify"
    return {"key": key, "title": title, "searched": searched, "source": source,
            "records": records if records is not None else sum(_records(c) for c in calls if c.ok),
            "credits": round(sum(c.credits for c in calls), 4),
            "status": status, "mode": "live" if live else ("replay" if any(c.cache_hit for c in calls) else "no call"),
            "recorded_at": recorded[-1] if recorded and not live else None,
            "calls": len(calls), "pointers": pointers, "note": note or "; ".join(c.reason for c in misses if c.reason)[:300]}


# ---- the run -----------------------------------------------------------------
def run_guided(run, case: dict, as_of: str, since: str) -> None:
    store: Store = run.store
    uid = run.req["user_id"]
    st = U.state(store, uid)
    conf, answers = st.get("confirmed") or {}, st.get("answers") or {}
    url = (store.q("SELECT profile_url FROM users WHERE user_id=?", uid) or [{"profile_url": None}])[0]["profile_url"]
    store.x("INSERT OR IGNORE INTO user_runs VALUES (?,?,?)", uid, run.run_id, now())
    day = as_of
    mine = f"user:{uid}:{day}:{h(conf, answers)}"         # unchanged inputs on the same day reuse every step
    shared = f"shared:{day}"                               # insurers and job posts are the same for everyone
    tc = lambda step: Tracked(store, run.run_id, step, mode=run.mode, started=run.t0)
    trail: list[dict] = []
    case["persona"] = {"persona_id": uid, "consent": True}

    # 1. You
    def you():
        c = tc("you")
        out = {"pd": None, "status": "none"}
        if url:
            r = c.call("/person/enrich", U.enrich_body(url))
            status, pd, _ = person_entry(r.data) if r.ok else ("error", None, "")
            out = {"pd": pd if status == "matched" else None, "status": status, "retrieved_at": r.retrieved_at}
        alarm = R.job_change(out["pd"], since, as_of, out.get("retrieved_at") or now()) if out["pd"] else None
        ptr = [{"record": "crustdata /person/enrich", "field_path": i["source"]["field_path"], "record_date": i["source"].get("record_date"),
                "retrieved_at": i["source"].get("retrieved_at")} for i in (st.get("intake") or []) if i.get("source")]
        out["alarm"] = alarm
        out["trail"] = trail_entry("you", "You", "your public work record (profile you agreed to)", "Crustdata /person/enrich",
                                   c.calls, out["status"] == "matched", ptr,
                                   note="" if out["status"] == "matched" else f"record status: {out['status']}; your answers are used")
        return out
    def add(name: str, entry: dict) -> None:
        e2 = dict(entry)
        if name in run.skipped:
            e2["reused"] = True
            e2["note"] = ((e2.get("note") or "") + " Reused from the step store: no new call this run.").strip()
        trail.append(e2)

    y = run.step("g_you", [url, since], you, scope=mine)
    add("g_you", y["trail"])
    case["alarm"] = y.get("alarm")

    # 2. Your employer (group level only)
    cid = (conf.get("company_id") or {}).get("value")
    employer = (conf.get("employer") or {}).get("value")
    def emp():
        c = tc("employer")
        if not cid:
            return {"facts": [], "trail": trail_entry("employer", "Your employer", "no employer record id", "Crustdata /company/enrich",
                                                       [], False, [], note="skipped: no employer on your confirmed profile")}
        r = c.call("/company/enrich", {"crustdata_company_ids": [cid], "fields": ["basic_info", "headcount"]})
        cd = None
        for item in (r.data or []) if r.ok else []:
            for m in item.get("matches") or []:
                cd = m.get("company_data")
        pts = [p for p in ((cd or {}).get("headcount") or {}).get("timeseries") or [] if p.get("employee_count") is not None]
        ptr = [{"record": "crustdata /company/enrich", "record_id": str(cid), "field_path": f"headcount.timeseries[{i}].employee_count",
                "record_date": p["date"], "retrieved_at": r.retrieved_at} for i, p in list(enumerate(pts))[-3:]]
        return {"points": pts, "name": ((cd or {}).get("basic_info") or {}).get("name") or employer, "retrieved_at": r.retrieved_at,
                "trail": trail_entry("employer", "Your employer", f"company record {cid} ({employer}): staff profile counts over time",
                                     "Crustdata /company/enrich", c.calls, bool(pts), ptr, records=len(pts))}
    e = run.step("g_employer", [cid], emp, scope=mine)
    add("g_employer", e["trail"])
    _group_beliefs(store, cid, e, run.run_id)

    # 3. People like you (job posts at similar employers)
    def ppl():
        c = tc("people")
        b = peers.benchmark(c, since, as_of)
        ptr = [{"record": "crustdata /job/search", "field_path": "total_count", "record_date": as_of,
                "retrieved_at": (b.get("source") or {}).get("retrieved_at"), "passage": json.dumps(b.get("filter"))[:400]}]
        ptr += [{"record": "crustdata /job/search", "field_path": f"content.description[{s['char_range'][0]}:{s['char_range'][1]}]",
                 "passage": s["passage"], "url": s["url"], "record_date": s["date_added"], "retrieved_at": s.get("retrieved_at")}
                for s in b.get("samples", [])]
        return {"benchmark": b, "trail": trail_entry("people", "People like you", "job posts since " + since +
                                                      " by logistics employers in India that mention cover", "Crustdata /job/search",
                                                      c.calls, b.get("total") is not None, ptr, records=b.get("total"))}
    pp = run.step("g_people", [since, as_of, load_rules()["peer_benchmark"]], ppl, scope=shared)
    add("g_people", pp["trail"])
    case["peer_benchmark"] = pp["benchmark"]

    # 4. Insurers (from data)
    def ins():
        c = tc("insurers")
        res = find_insurers(c, c)
        ptr = [f["source"] for it in res["items"] for f in it["facts"] if f.get("source")][:12]
        res.pop("search_result", None); res.pop("enrich_result", None)
        return {"res": res, "trail": trail_entry("insurers", "Insurers", "Indian companies with a health-insurer legal name; "
                                                 "selection rules in rules.yaml", "Crustdata /company/search, /company/enrich",
                                                 c.calls, res["status"] == "found", ptr, records=len(res["items"]),
                                                 note=res.get("missing", ""))}
    ii = run.step("g_insurers", [load_rules()["insurers"]], ins, scope=shared)
    add("g_insurers", ii["trail"])
    case["insurers"] = ii["res"]

    # 5. Gaps (rules file; no data call)
    facts = profile_facts(conf, answers)
    gl = R.gaps(facts, y.get("alarm"))
    trail.append({"key": "gaps", "title": "Gaps", "searched": "your confirmed facts against rules.yaml", "source": "rules.yaml",
                  "records": len(gl), "credits": 0, "status": "computed", "mode": "no call", "recorded_at": None,
                  "pointers": [{"record": "rules.yaml", "field_path": f"gaps[{g['rule_id']}]"} for g in gl],
                  "note": "no lookup: rules applied to the facts above"})
    case.update(gaps=gl, facts=facts, trail=trail)
    for q in _answer_questions(answers):
        run.questions.append(q)
    record_beliefs(store, uid, facts, run.run_id, gl, next_step_key(store, uid, y.get("alarm")))
    U.save_state(store, uid, stage="dashboard", last_run_id=run.run_id)
    if y.get("alarm") and y["alarm"].get("status") == "job_change":
        a = y["alarm"]
        actions.prepare(store, run.run_id, "conversion_request", uid,
                        f"Ask the old employer's insurer to move your cover from {a['old_employer']} to a personal policy by {a['conversion_deadline']}",
                        {"old_employer": a["old_employer"], "cover_end_date": a["cover_end_date"], "convert_by": a["conversion_deadline"]})


def _group_beliefs(store: Store, cid, e: dict, run_id: str) -> None:
    """Staff counts at the employer as dated group beliefs (group level; the minimum group size applies)."""
    if not cid or not e.get("points"):
        return
    n = int(load_rules()["diary"]["headcount_points"])
    minimum = int(load_rules()["beliefs"]["min_group_size"])
    for p in e["points"][-n:]:
        v = int(p["employee_count"])
        src = [{"record": "crustdata /company/enrich", "record_id": str(cid), "field_path": "headcount.timeseries[].employee_count",
                "record_date": p["date"], "retrieved_at": e.get("retrieved_at")}]
        _version(store, f"company:{cid}", "headcount", f"Staff profiles at {e.get('name')}", v if v >= minimum else None, v,
                 p["date"], src, v < minimum)


# ---- facts, beliefs, diary ------------------------------------------------------
LABELS = {"employer": "Where you work", "role": "Your job", "start_date": "Started", "city": "Your city", "age_band": "Your age"}


def profile_facts(conf: dict, answers: dict) -> list[dict]:
    out = []
    for k, title in LABELS.items():
        c = conf.get(k)
        if not c or c.get("value") in (None, ""):
            continue
        out.append({"fact_id": k, "statement": f"{title}: {c['value']}", "value": c["value"], "label": c["label"],
                    "source": c.get("source") or {"record": "you told us", "field_path": f"confirm.{k}"}})
    dep = answers.get("dependants") or []
    if dep and "not_sure" not in dep:
        n = len([d for d in dep if d != "just_me"])
        out.append({"fact_id": "dependants", "statement": "People who depend on you: " + (", ".join(d.replace("_", " ") for d in dep)),
                    "value": n, "label": "told", "source": {"record": "you told us", "field_path": "answers.dependants"}})
    ins = answers.get("insurance_now") or []
    if ins and "not_sure" not in ins:
        held = (["employer_group_health"] if "from_work" in ins else []) + (["personal_health"] if "bought_myself" in ins else [])
        words = {"from_work": "from work", "bought_myself": "bought yourself", "none": "none"}
        out.append({"fact_id": "cover_held", "statement": "Insurance now: " + ", ".join(words.get(i, i) for i in ins),
                    "value": held, "label": "told", "source": {"record": "you told us", "field_path": "answers.insurance_now"}})
    return out


def _answer_questions(answers: dict) -> list[dict]:
    q = []
    if "not_sure" in (answers.get("dependants") or []):
        q.append({"question": "When you know who depends on your income, tell us and we will check again.",
                  "why": "Life cover depends on this, so we did not guess."})
    if "not_sure" in (answers.get("insurance_now") or []):
        q.append({"question": "Ask HR whether your job gives you health cover, then tell us.",
                  "why": "We do not guess what cover you have, so gaps about it were not checked."})
    if "bought_myself" in (answers.get("insurance_now") or []):
        q.append({"question": "Is the insurance you bought for hospital and doctor costs? If not, tell us what it covers.",
                  "why": "We read it as health cover; this changes what is missing."})
    return q


def next_step_key(store: Store, uid: str, alarm: dict | None) -> str:
    st = U.state(store, uid)
    ch = st.get("choice") or {}
    parts = [f"apply:{ch.get('company_id')}" if ch else "choose_insurer"]
    if alarm and alarm.get("status") == "job_change":
        parts.append("convert")
    return "+".join(parts)


def record_beliefs(store: Store, uid: str, facts: list[dict], trigger: str, gaps: list[dict], next_step: str) -> None:
    U.ensure(store)
    t = now()
    for f in facts:
        val = json.dumps(f.get("value"), sort_keys=True)
        last = store.q("SELECT version, value, label FROM persona_beliefs WHERE persona_id=? AND belief_key=? AND valid_to IS NULL "
                       "ORDER BY version DESC LIMIT 1", uid, f["fact_id"])
        if last and last[0]["value"] == val and last[0]["label"] == f["label"]:
            store.x("UPDATE persona_beliefs SET last_checked=? WHERE persona_id=? AND belief_key=? AND version=?",
                    t, uid, f["fact_id"], last[0]["version"])
            continue
        v = 1
        if last:
            store.x("UPDATE persona_beliefs SET valid_to=? WHERE persona_id=? AND belief_key=? AND version=?", t, uid, f["fact_id"], last[0]["version"])
            v = last[0]["version"] + 1
        store.x("INSERT INTO persona_beliefs VALUES (?,?,?,?,?,?,?,?,?,?,?)", uid, f["fact_id"], v, f["statement"], val, f["label"],
                json.dumps(f.get("source")), t, None, trigger, t)
    store.x("INSERT INTO persona_snapshots VALUES (?,?,?,?,?)", uid, t, trigger, json.dumps(sorted(g["rule_id"] for g in gaps)), next_step)


def facts_as_of(store: Store, uid: str, as_of: str | None) -> list[dict]:
    U.ensure(store)
    rows = store.q("SELECT * FROM persona_beliefs WHERE persona_id=? ORDER BY belief_key, version", uid)
    out = []
    for r in rows:
        if as_of and (r["valid_from"][:10] > as_of or (r["valid_to"] and r["valid_to"][:10] <= as_of)):
            continue
        if not as_of and r["valid_to"]:
            continue
        out.append({"fact_id": r["belief_key"], "statement": r["statement"], "value": json.loads(r["value"]), "label": r["label"],
                    "source": json.loads(r["source"]) if r["source"] else None, "last_checked": r["last_checked"],
                    "valid_from": r["valid_from"], "version": r["version"]})
    return out


def diary(store: Store, uid: str) -> list[dict]:
    """Only the persona's own beliefs and group beliefs (>= minimum group size) for the persona's employer."""
    U.ensure(store)
    snaps = store.q("SELECT ts, gaps, next_step FROM persona_snapshots WHERE persona_id=? ORDER BY ts", uid)

    def changed(ts: str) -> tuple[bool, bool]:
        before = [s for s in snaps if s["ts"] < ts]
        at = [s for s in snaps if s["ts"] >= ts][:1]
        if not at:
            return False, False
        if not before:
            return bool(json.loads(at[0]["gaps"])), True
        return before[-1]["gaps"] != at[0]["gaps"], before[-1]["next_step"] != at[0]["next_step"]

    out = []
    rows = store.q("SELECT * FROM persona_beliefs WHERE persona_id=? ORDER BY valid_from, belief_key, version", uid)
    prev: dict[str, Any] = {}
    for r in rows:
        g, n = changed(r["valid_from"])
        out.append({"date": r["valid_from"][:10], "subject": "You", "subject_kind": "you", "new": r["statement"],
                    "previous": prev.get(r["belief_key"]), "trigger": f"run {r['trigger']}",
                    "source": json.loads(r["source"]) if r["source"] else None, "label": r["label"],
                    "gap_changed": g, "next_step_changed": n})
        prev[r["belief_key"]] = r["statement"]
    cid = ((U.state(store, uid).get("confirmed") or {}).get("company_id") or {}).get("value")
    minimum = int(load_rules()["beliefs"]["min_group_size"])
    if cid:
        gp = store.q("SELECT * FROM beliefs WHERE group_key=? ORDER BY version", f"company:{cid}")
        last = None
        for b in gp:
            if b["value"] is None or b["n"] < minimum:
                continue  # group too small: never shown
            out.append({"date": b["valid_from"], "subject": b["statement"].replace("Staff profiles at ", "Staff at ") + " (group)",
                        "subject_kind": "group", "new": f"{int(b['value']):,} staff profiles",
                        "previous": f"{int(last):,} staff profiles" if last is not None else None,
                        "trigger": "dated point in the company record", "source": (json.loads(b["sources"]) or [None])[0],
                        "label": "checked", "gap_changed": False, "next_step_changed": False})
            last = b["value"]
    out.sort(key=lambda d: (d["date"], d["subject_kind"]), reverse=True)
    return out


def dashboard(store: Store, uid: str, as_of: str | None = None) -> dict:
    U.ensure(store)
    st = U.state(store, uid)
    rid = st.get("last_run_id")
    run = store.q("SELECT status, result FROM runs WHERE run_id=?", rid) if rid else []
    case = json.loads(run[0]["result"]) if run and run[0]["result"] else {}
    status = "none" if not rid else (run[0]["status"] if run else "running")
    facts = facts_as_of(store, uid, as_of)
    days = sorted({r["valid_from"][:10] for r in store.q("SELECT valid_from FROM persona_beliefs WHERE persona_id=?", uid)}
                  | {d["date"] for d in diary(store, uid)})
    snap = store.q("SELECT gaps FROM persona_snapshots WHERE persona_id=? AND substr(ts,1,10)<=? ORDER BY ts DESC LIMIT 1",
                   uid, as_of or "9999") if as_of else []
    gaps = case.get("gaps") or []
    if as_of and snap:
        keep = set(json.loads(snap[0]["gaps"]))
        gaps = [g for g in gaps if g["rule_id"] in keep]
    ins = case.get("insurers") or {"items": [], "note": "", "status": "not run yet"}
    choice = st.get("choice")
    acts = actions.list_all(store, None, uid) if rid else []
    act = next((a for a in acts if a["persona_id"] == uid and a["action"] == "submit_application"), None)
    conv = next((a for a in acts if a["persona_id"] == uid and a["action"] == "conversion_request"), None)
    run_ids = [r["run_id"] for r in store.q("SELECT run_id FROM user_runs WHERE user_id=?", uid)]
    cost = {"credits": 0.0, "inr": 0.0}
    for r_ in run_ids:
        c = store.run_cost(r_); cost["credits"] += c["credits"]; cost["inr"] += c["inr"]
    last_checked = max((f.get("last_checked") or "" for f in facts), default=None) or None
    return {"user": {"user_id": uid, "mode": U.mode_of(store, uid), "stage": st.get("stage"), "last_checked": last_checked},
            "as_of": as_of or date.today().isoformat(), "dates": days,
            "run": {"run_id": rid, "status": status},
            "profile": facts,
            "graph_case": {"facts": [dict(f, fact_id={"employer": "current_employer", "role": "current_title"}.get(f["fact_id"], f["fact_id"]))
                                     for f in facts], "peer_benchmark": case.get("peer_benchmark") if (not as_of or (rid and days and as_of >= days[0])) else None},
            "insurers": {k: ins.get(k) for k in ("note", "selection", "items", "status", "missing", "dropped")},
            "gaps": gaps, "questions": case.get("questions") or [], "cannot_verify": case.get("cannot_verify") or [],
            "trail": case.get("trail") or [],
            "next_step": {"choices": [{"company_id": i["company_id"], "name": i["name"]} for i in ins.get("items") or []],
                          "chosen": choice, "action": act, "conversion": conv},
            "diary": diary(store, uid), "cost": {"credits": round(cost["credits"], 4), "inr": round(cost["inr"], 2)}}


def choose(store: Store, uid: str, company_id: int) -> dict:
    st = U.state(store, uid)
    rid = st.get("last_run_id")
    case = json.loads((store.q("SELECT result FROM runs WHERE run_id=?", rid) or [{"result": "{}"}])[0]["result"] or "{}")
    item = next((i for i in (case.get("insurers") or {}).get("items") or [] if i["company_id"] == company_id), None)
    if not item:
        raise U.LoginError(400, "That insurer is not in the list found for you.")
    gaps = [g for g in case.get("gaps") or [] if g["severity"] != "low"]
    if not gaps:
        raise U.LoginError(400, "Nothing is missing, so there is no application to prepare.")
    g = gaps[0]
    conf = st.get("confirmed") or {}
    payload = {"insurer": item["name"], "insurer_record": company_id, "insurer_basis": "chosen by you (told)",
               "cover": g["called_for"], "rule_id": g["rule_id"], "premium": "to be quoted by the insurer",
               "applicant": {k: (conf.get(k) or {}).get("value") for k in ("age_band", "city")},
               "answers": st.get("answers")}
    a = actions.prepare(store, rid, "submit_application", uid,
                        f"Send a filled-in application to {item['name']} for {g['called_for']} (rule {g['rule_id']})", payload)
    U.save_state(store, uid, choice={"company_id": company_id, "name": item["name"]})
    return a
