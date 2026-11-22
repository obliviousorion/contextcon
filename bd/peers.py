"""Peer benchmark: share of peer employers' job posts that mention cover. Count-only queries (free).

A post that is silent on benefits counts as "not mentioned", never as "no cover".
"""
from __future__ import annotations

from .config import load_rules
from .crust import Crust


def base_filter(since: str, rules: dict, *extra: dict) -> dict:
    pb = rules["peer_benchmark"]
    return {"op": "and", "conditions": [
        {"field": "company.basic_info.industries", "type": "in", "value": [pb["industry"]]},
        {"field": "location.country", "type": "=", "value": pb["country"]},
        {"field": "metadata.date_added", "type": "=>", "value": since}, *extra]}


def phrase_cond(p: str) -> dict:
    return {"field": "content.description", "type": "[.]", "value": p}


def any_cover(rules: dict) -> dict:
    return {"op": "or", "conditions": [phrase_cond(p) for p in rules["peer_benchmark"]["phrases"]]}


def count(c: Crust, flt: dict) -> tuple[int | None, str | None, str | None]:
    r = c.job_search({"filters": flt, "limit": 0, "aggregations": [{"type": "count"}]})
    if r.kind == "held":
        raise HeldRun(r.reason)
    if not r.ok:
        return None, r.reason, r.retrieved_at
    return int((r.data or {}).get("total_count") or 0), None, r.retrieved_at


class HeldRun(Exception):
    pass


def benchmark(c: Crust, since: str, as_of: str, with_roles: bool = False) -> dict:
    rules = load_rules()
    pb = rules["peer_benchmark"]
    flt = base_filter(since, rules)
    total, err, ts = count(c, flt)
    if total is None:
        return {"cannot_verify": f"job search failed: {err}", "filter": flt, "as_of": as_of}
    phrases = []
    for p in pb["phrases"]:
        n, e, _ = count(c, base_filter(since, rules, phrase_cond(p)))
        phrases.append({"phrase": p, "count": n, "share": round(n / total, 4) if n is not None and total else None,
                        **({"cannot_verify": f"count not settled: {e}"} if n is None else {})})
    anyf = base_filter(since, rules, any_cover(rules))
    n_any, e_any, _ = count(c, anyf)
    out = {"filter": flt, "any_cover_filter": anyf, "as_of": as_of, "since": since, "total": total,
           "phrases": phrases,
           "any_cover": {"count": n_any, "share": round(n_any / total, 4) if n_any is not None and total else None},
           "note": pb["note"],
           "source": {"record": "crustdata /job/search (count aggregation, limit 0)", "retrieved_at": ts,
                      "field_path": "total_count", "record_date": as_of}}
    if with_roles:
        roles = []
        for role, word in pb["roles"].items():
            t = {"field": "job_details.title", "type": "(.)", "value": word}
            rt, _, _ = count(c, base_filter(since, rules, t))
            rc, _, _ = count(c, base_filter(since, rules, t, any_cover(rules)))
            roles.append({"role": role, "title_word": word, "total": rt, "with_cover": rc})
        out["by_role"] = roles
    # quoted passages: a few rows of the any-cover query, newest first
    samples = []
    if pb.get("sample_rows"):
        r = c.job_search({"filters": anyf, "limit": int(pb["sample_rows"]),
                          "sorts": [{"field": "metadata.date_added", "order": "desc"}]})
        if r.kind == "held":
            raise HeldRun(r.reason)
        for j in ((r.data or {}).get("job_listings") or []) if r.ok else []:
            desc = (j.get("content") or {}).get("description") or ""
            low = desc.lower()
            hit = next(((p, low.find(p.lower())) for p in pb["phrases"] if low.find(p.lower()) >= 0), None)
            if not hit:
                continue  # pointer does not resolve: no passage, no claim
            p, i = hit
            a, b = max(0, i - 80), min(len(desc), i + len(p) + 80)
            samples.append({"job_id": str(j.get("crustdata_job_id")), "url": (j.get("job_details") or {}).get("url"),
                            "company": ((j.get("company") or {}).get("basic_info") or {}).get("name"),
                            "date_added": (j.get("metadata") or {}).get("date_added"), "phrase": p,
                            "passage": desc[a:b], "char_range": [a, b],
                            "field_path": "content.description", "retrieved_at": r.retrieved_at})
    out["samples"] = samples
    return out
