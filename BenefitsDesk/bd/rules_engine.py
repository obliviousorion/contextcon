"""Pure rule evaluation from rules.yaml: job change, cover gaps, employer package, insurer ranking."""
from __future__ import annotations

from datetime import date, timedelta
from typing import Any

from .config import load_rules
from .facts import d, jobs


def _months_back(x: date, n: int) -> date:
    m = x.month - n
    y = x.year + (m - 1) // 12
    return date(y, (m - 1) % 12 + 1, 1)


def job_change(pd: dict, since: str, as_of: str, retrieved_at: str, rules: dict | None = None) -> dict:
    """Detect a new employer by crustdata_company_id. Same id = same company (promotion: no alarm)."""
    rules = rules or load_rules()
    jc, tol = rules["job_change"], int(rules["dates"]["tolerance_months"])
    s, a = d(since), d(as_of)
    s_tol = _months_back(s, tol)
    rec = "crustdata /person/enrich"
    rid = str(pd.get("crustdata_person_id") or "")
    src = lambda path, rd=None: {"record": rec, "record_id": rid, "field_path": path,
                                 "retrieved_at": retrieved_at, "record_date": rd}
    cur, past = jobs(pd)
    main = [(p, j) for p, j in cur if j.get("is_default")]
    if len(cur) > 1 and not main:
        return {"status": "cannot_verify", "explanation": "Several current jobs and none is marked main (is_default).",
                "sources": [src("experience.employment_details.current")]}
    main = main or cur[:1]
    ended = sorted([(p, j) for p, j in past if d(j.get("end_date"))], key=lambda pj: pj[1]["end_date"], reverse=True)
    if main:
        np, nj = main[0]
        start = d(nj.get("start_date"))
        # the previous employer: a past job that ended most recently, at or before the new start (+tolerance)
        prev = [(p, j) for p, j in ended if start is None or d(j["end_date"]) <= _months_back(start, -tol)]
        if not prev:
            return {"status": "no_change_on_record",
                    "explanation": "One current employer and no earlier job on the stored copy.",
                    "sources": [src(f"{np}.start_date", (nj.get("start_date") or "")[:10])]}
        op, oj = prev[0]
        same = nj.get(jc["compare_on"]) is not None and nj.get(jc["compare_on"]) == oj.get(jc["compare_on"])
        if same:
            return {"status": "same_company", "old_employer": oj.get("name"), "new_employer": nj.get("name"),
                    "change_date": (nj.get("start_date") or "")[:10],
                    "explanation": f"Role change inside the same company (same {jc['compare_on']}): not a job change, no alarm.",
                    "sources": [src(f"{np}.{jc['compare_on']}"), src(f"{op}.{jc['compare_on']}")]}
        if start is None or start < s_tol:
            return {"status": "no_change_on_record",
                    "explanation": f"The latest employer change on record started {nj.get('start_date','?')[:10]}, before the window ({since}, one month tolerance).",
                    "sources": [src(f"{np}.start_date", (nj.get("start_date") or "")[:10])]}
        end = d(oj["end_date"])
        deadline = end + timedelta(days=int(jc["conversion_window_days"]))
        sister = any(nj.get("crustdata_company_id") in g and oj.get("crustdata_company_id") in g for g in jc["sister_groups"])
        passed = deadline < a
        return {"status": "job_change", "old_employer": oj.get("name"), "new_employer": nj.get("name"),
                "change_date": start.isoformat(), "cover_end_date": end.isoformat(),
                "conversion_deadline": deadline.isoformat(), "deadline_passed": passed, "sister_company": sister,
                "explanation": (f"New employer by {jc['compare_on']} ({oj.get(jc['compare_on'])} -> {nj.get(jc['compare_on'])}). "
                                f"Rule R-ALARM-1: group cover ends on the last day at the old employer ({end.isoformat()}, stored as "
                                f"first of month, so +/- {tol} month). Rule R-ALARM-2: ask to convert by {deadline.isoformat()} "
                                f"({jc['conversion_window_days']} days; the insurer's own window may differ)."
                                + (f" That date is before {as_of}: the request asks the insurer whether conversion is still possible."
                                   if passed else "")),
                "sources": [src(f"{np}.crustdata_company_id"), src(f"{np}.start_date", start.isoformat()),
                            src(f"{op}.crustdata_company_id"), src(f"{op}.end_date", end.isoformat())]}
    # no current job
    if ended:
        op, oj = ended[0]
        end = d(oj["end_date"])
        in_window = end >= s_tol and end <= _months_back(a, -tol)
        return {"status": "no_change_on_record", "old_employer": oj.get("name"), "cover_end_date": end.isoformat(),
                "employment_ended": True, "ended_in_window": in_window,
                "explanation": (f"No current employer on the stored copy. The last job, at {oj.get('name')}, ended "
                                f"{end.isoformat()} (+/- {tol} month){' inside' if in_window else ', before'} the window from {since}. "
                                "No new employer is on record. The record has no refresh date, so we cannot verify that nothing changed since."),
                "sources": [src(f"{op}.end_date", end.isoformat())]}
    return {"status": "cannot_verify", "explanation": "No employment on the stored copy.",
            "sources": [src("experience.employment_details")]}


def gaps(facts: list[dict], alarm: dict | None, rules: dict | None = None) -> list[dict]:
    """Facts (told/checked only) -> gaps. Guessed facts never enter."""
    rules = rules or load_rules()
    usable = {f["fact_id"]: f for f in facts if f["label"] in ("told", "checked") and not f.get("cannot_verify")}
    held = set(usable.get("cover_held", {}).get("value") or [])
    dep = usable.get("dependants", {}).get("value")
    budget = usable.get("monthly_budget_inr", {}).get("value")
    role = usable.get("role_group", {}).get("value")
    ended = bool(alarm and (alarm.get("status") == "job_change" or alarm.get("employment_ended")))
    out = []
    for r in rules["gaps"]:
        w, used, ok = r["when"], [], True
        if "cover_held_none_of" in w:
            ok &= "cover_held" in usable and not (held & set(w["cover_held_none_of"])); used.append("cover_held")
        if "cover_held_has" in w:
            ok &= w["cover_held_has"] in held; used.append("cover_held")
        if "employment_ended" in w:
            ok &= ended == w["employment_ended"]; used.append("alarm")
        if "dependants_at_least" in w:
            ok &= isinstance(dep, (int, float)) and dep >= w["dependants_at_least"]; used.append("dependants")
        if "role_group_in" in w:
            ok &= role in w["role_group_in"]; used.append("role_group")
        if "budget_below" in w:
            ok &= isinstance(budget, (int, float)) and budget < w["budget_below"]; used.append("monthly_budget_inr")
        if ok:
            out.append({"rule_id": r["id"], "cover": r["cover"], "called_for": r["called_for"],
                        "held": ", ".join(sorted(held)) or "none", "severity": r["severity"],
                        "explanation": r["explanation"], "facts_used": sorted(set(used))})
    return out


def package(rules: dict | None = None) -> list[dict]:
    rules = rules or load_rules()
    return [{"role": role, "items": items} for role, items in rules["package"].items()]


def rank_insurers(insurers: list[dict], rules: dict | None = None) -> list[dict]:
    """Rank on verified regulator figures only. Fewer than min_figures verified -> not ranked."""
    rules = rules or load_rules()
    spec, need = rules["insurers"]["ranking"], rules["insurers"]["min_figures"]
    ok = [i for i in insurers if sum(1 for f in i["figures"] if not f.get("cannot_verify")) >= need]
    for metric, m in spec.items():
        vals = [f["value"] for i in ok for f in i["figures"] if f["metric"] == metric and not f.get("cannot_verify")]
        lo, hi = (min(vals), max(vals)) if vals else (0, 1)
        for i in ok:
            v = next((f["value"] for f in i["figures"] if f["metric"] == metric and not f.get("cannot_verify")), None)
            norm = 0.0 if v is None or hi == lo else (v - lo) / (hi - lo)
            if m["better"] == "lower":
                norm = 1 - norm
            i.setdefault("_score", 0.0)
            i["_score"] += m["weight"] * norm
            i.setdefault("reasons", []).append(f"{metric} = {v} (weight {m['weight']}, {m['better']} is better)")
    ok.sort(key=lambda i: -i["_score"])
    for n, i in enumerate(ok, 1):
        i["rank"] = n
        i["score"] = round(i.pop("_score"), 3)
    for i in insurers:
        if i not in ok:
            i["rank"] = None
            i.setdefault("reasons", []).append(f"not ranked: fewer than {need} verified regulator figures")
    return sorted(insurers, key=lambda i: (i["rank"] is None, i["rank"] or 0))
