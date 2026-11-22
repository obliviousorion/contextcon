"""Insurers from data, not a fixed list.

1. Crustdata company search with the selection rules in rules.yaml (Indian companies with a health-insurer
   legal name). 2. Keep legal entities only, one record per web domain. 3. Enrich up to `enrich_max` for
   founding year, headcount history and offices. Every value carries its source field and date.

Company facts are shown as company facts. They are never used to rank insurers and never presented as a
measure of claim quality. Claim and complaint figures stay CANNOT VERIFY (no quotable regulator source).
"""
from __future__ import annotations

from .config import load_rules
from .crust import Crust, Result
from .peers import HeldRun

NOTE = ("These are company facts from the record (when it was founded, how many staff profiles it has, where its "
        "offices are). They say nothing about how well an insurer pays claims, so the list is not ranked.")
CLAIMS_MISSING = ("claim and complaint figures: the regulator (IRDAI) publishes them only inside a PDF annual report, "
                  "and no quotable row has been extracted, so they are not shown")


def search_body(rules: dict) -> dict:
    s = rules["search"]
    return {"filters": {"op": "and", "conditions": [
        {"op": "or", "conditions": [{"field": "basic_info.name", "type": "[.]", "value": p} for p in s["name_phrases"]]},
        {"field": "locations.country", "type": "=", "value": s["country"]}]},
        "fields": ["basic_info.name", "basic_info.year_founded", "basic_info.primary_domain", "basic_info.all_domains",
                   "basic_info.company_type", "locations.headquarters"],
        "sorts": [{"field": "basic_info.name", "order": "asc"}], "limit": int(s["limit"])}


def select(companies: list[dict], rules: dict) -> tuple[list[dict], list[dict]]:
    """-> (kept, dropped with reason). Pure: rules.yaml decides."""
    kept, dropped, seen = [], [], set()
    for co in companies:
        bi = co.get("basic_info") or {}
        name, dom = bi.get("name") or "", (bi.get("primary_domain") or "").lower()
        why = None
        if bi.get("company_type") not in rules["keep_company_types"]:
            why = f"company type {bi.get('company_type')!r} is not a company"
        elif any(not bi.get(f) for f in rules["require"]):
            why = "no " + " / ".join(f for f in rules["require"] if not bi.get(f)) + " on record"
        elif dom in rules["generic_domains"]:
            why = f"generic web host {dom}"
        elif any(w.lower() in name.lower() for w in rules["exclude_name_words"]):
            why = "name looks like a branch, agent or service firm"
        elif rules.get("one_record_per_domain") and dom in seen:
            why = f"same web domain as a record already kept ({dom})"
        if why:
            dropped.append({"name": name, "company_id": co.get("crustdata_company_id"), "reason": why})
        else:
            seen.add(dom)
            kept.append(co)
    kept.sort(key=lambda c: ((c.get("basic_info") or {}).get("name") or "").lower())
    return kept, dropped


def _src(field: str, r: Result, record_date: str | None = None, cid=None) -> dict:
    return {"record": f"crustdata {r.endpoint}", "record_id": str(cid) if cid else None, "field_path": field,
            "record_date": record_date, "retrieved_at": r.retrieved_at}


def company_facts(cd: dict, r: Result) -> list[dict]:
    cid = cd.get("crustdata_company_id")
    bi, hc, lo = cd.get("basic_info") or {}, cd.get("headcount") or {}, cd.get("locations") or {}
    out = []
    if bi.get("year_founded"):
        out.append({"label": "Founded", "value": bi["year_founded"], "source": _src("basic_info.year_founded", r, None, cid)})
    ts = [p for p in hc.get("timeseries") or [] if p.get("date") and p.get("employee_count") is not None]
    if ts:
        first, last = ts[0], ts[-1]
        out.append({"label": "Staff profiles (latest point)", "value": f"{last['employee_count']:,} on {last['date']}",
                    "source": _src(f"headcount.timeseries[{len(ts) - 1}].employee_count", r, last["date"], cid)})
        out.append({"label": "Staff profiles (earliest point)", "value": f"{first['employee_count']:,} on {first['date']}",
                    "source": _src("headcount.timeseries[0].employee_count", r, first["date"], cid)})
        out.append({"label": "Note", "value": "profile-derived counts shown side by side; not a growth figure",
                    "source": _src("headcount.timeseries", r, last["date"], cid)})
    if lo.get("headquarters"):
        out.append({"label": "Head office", "value": lo["headquarters"], "source": _src("locations.headquarters", r, None, cid)})
    offices = lo.get("all_office_addresses") or []
    out.append({"label": "Other offices on record", "value": len(offices), "source": _src("locations.all_office_addresses", r, None, cid)})
    return out


def find(c_search: Crust, c_enrich: Crust) -> dict:
    """-> {items, note, selection, status, trail:{search:..., enrich:...}}"""
    rules = load_rules()["insurers"]
    body = search_body(rules)
    r = c_search.call("/company/search", body)
    if r.kind == "held":
        raise HeldRun(r.reason)
    out = {"note": NOTE, "selection": {"search": body, "rules": {k: rules[k] for k in
           ("keep_company_types", "require", "generic_domains", "exclude_name_words", "one_record_per_domain", "enrich_max", "order")}},
           "items": [], "dropped": [], "search_result": r}
    if not r.ok or not (r.data or {}).get("companies"):
        out.update(status="searched, cannot verify",
                   missing=("company search returned no insurer" if r.ok else f"company search not settled: {r.reason}"))
        return out
    kept, dropped = select(r.data["companies"], rules)
    out["dropped"] = dropped
    kept = kept[: int(rules["enrich_max"])]
    if not kept:
        out.update(status="searched, cannot verify", missing="no search result met the selection rules in rules.yaml")
        return out
    e = c_enrich.call("/company/enrich", {"crustdata_company_ids": sorted(k["crustdata_company_id"] for k in kept),
                                          "fields": ["basic_info", "headcount", "locations"]})
    if e.kind == "held":
        raise HeldRun(e.reason)
    out["enrich_result"] = e
    by = {}
    for item in (e.data or []) if e.ok else []:
        for m in item.get("matches") or []:
            cd = m.get("company_data") or {}
            by[cd.get("crustdata_company_id")] = cd
    for k in kept:
        cid = k["crustdata_company_id"]
        cd = by.get(cid)
        facts = company_facts(cd, e) if cd else [
            {"label": "Founded", "value": (k.get("basic_info") or {}).get("year_founded"), "source": _src("basic_info.year_founded", r, None, cid)}]
        out["items"].append({"company_id": cid, "name": (k.get("basic_info") or {}).get("name"), "facts": facts,
                             "claims": {"cannot_verify": True, "missing": CLAIMS_MISSING},
                             **({} if cd else {"enrich_missing": f"company enrich not settled: {e.reason or 'no match'}"})})
    out["status"] = "found"
    return out


def shortlist(c: Crust, as_of: str) -> list[dict]:
    """Back-compatible shape for the employee_review case file: insurers found from data, no ranking."""
    res = find(c, c)
    items = []
    for it in res["items"]:
        items.append({"insurer": it["name"], "company_id": it["company_id"], "rank": None,
                      "figures": [{"metric": "claim and complaint figures", "cannot_verify": True, "missing": CLAIMS_MISSING}],
                      "company_facts": it["facts"], "reasons": [NOTE]})
    if not items:
        items.append({"insurer": "no insurer found", "rank": None, "company_facts": [], "reasons": [NOTE],
                      "figures": [{"metric": "insurer search", "cannot_verify": True, "missing": res.get("missing", "")}]})
    return items
