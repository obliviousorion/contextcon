"""Workplace beliefs about a GROUP (employer + function + city), never a named colleague.

Counts come from person search with limit 1 (we read total_count; one row is returned and charged,
and never stored or shown). New evidence closes the old version (valid_to) and opens a new one.
"""
from __future__ import annotations

import json
from datetime import date, timedelta

from .config import load_rules
from .crust import Crust
from .peers import HeldRun
from .store import Store, h


def _cond(field, typ, value):
    return {"field": field, "type": typ, "value": value}


def _count(c: Crust, conds: list[dict]) -> tuple[int | None, str | None, str | None]:
    r = c.person_search({"filters": {"op": "and", "conditions": conds}, "limit": 1,
                         "fields": ["basic_profile.location"]})
    if r.kind == "held":
        raise HeldRun(r.reason)
    if not r.ok:
        return None, r.reason, None
    return int((r.data or {}).get("total_count") or 0), None, r.retrieved_at


def group_conds(group: dict, kind: str) -> list[dict]:
    base = "experience.employment_details." + kind
    out = [_cond(f"{base}.company_id", "=", group["company_id"])]
    if group.get("city"):
        out.append(_cond("basic_profile.location.city", "=", group["city"]))
    if group.get("function"):
        out.append(_cond(f"{base}.function_category", "=", group["function"]))
    return out


def measure(c: Crust, group: dict, end: date, days: int) -> dict:
    start = end - timedelta(days=days)
    s, e = start.isoformat(), end.isoformat()
    cur = "experience.employment_details.current"
    past = "experience.employment_details.past"
    q = {
        "staff_now": group_conds(group, "current"),
        "joiners": group_conds(group, "current") + [_cond(f"{cur}.start_date", "=>", s), _cond(f"{cur}.start_date", "=<", e)],
        "leavers": group_conds(group, "past") + [_cond(f"{past}.end_date", "=>", s), _cond(f"{past}.end_date", "=<", e)],
        "contract_joiners": group_conds(group, "current") + [_cond(f"{cur}.start_date", "=>", s),
                                                             _cond(f"{cur}.employment_type", "=", "Contract")],
    }
    out = {"window": [s, e]}
    for k, conds in q.items():
        n, err, ts = _count(c, conds)
        out[k] = n
        out[k + "_filter"] = conds
        out[k + "_retrieved_at"] = ts
        if err:
            out[k + "_error"] = err
    return out


def beliefs_for(store: Store, c: Crust, group: dict) -> dict:
    rules = load_rules()["beliefs"]
    gkey = h(group["company_id"], group.get("function"), group.get("city"))
    minimum = int(rules["min_group_size"])
    days = int(rules["windows_days"])
    for at in rules["versions_at"]:
        m = measure(c, group, date.fromisoformat(at), days)
        n = m.get("staff_now")
        stmts = {
            "joiners": (f"People who joined this group in the {days} days to {at}", m.get("joiners")),
            "leavers": (f"People who left this group in the {days} days to {at}", m.get("leavers")),
            "contract_share": ("Share of recent joiners on contract terms",
                               (round(m["contract_joiners"] / m["joiners"], 3)
                                if m.get("joiners") and m.get("contract_joiners") is not None else None)),
        }
        for bkey, (stmt, val) in stmts.items():
            suppressed = n is None or n < minimum
            src = [{"record": "crustdata /person/search (total_count)", "field_path": "total_count",
                    "filter": m.get(f"{'joiners' if bkey != 'leavers' else 'leavers'}_filter"),
                    "retrieved_at": m.get("staff_now_retrieved_at"), "record_date": at}]
            _version(store, gkey, bkey, stmt, None if suppressed else val, n or 0, at, src, suppressed)
    rows = store.q("SELECT * FROM beliefs WHERE group_key=? ORDER BY belief_key, version", gkey)
    beliefs = []
    for r in rows:
        b = dict(r)
        b["sources"] = json.loads(b["sources"])
        b["suppressed"] = b["value"] is None and b["n"] < minimum
        if b["suppressed"]:
            b["reason"] = f"group too small: {b['n']} people on record, minimum {minimum}"
        beliefs.append(b)
    timeline = _timeline(c, group, rules)
    return {"group": {"key": gkey, **group}, "beliefs": beliefs, "timeline": timeline}


def _version(store: Store, gkey, bkey, stmt, val, n, at, src, suppressed) -> None:
    last = store.q("SELECT version, value, n, valid_from FROM beliefs WHERE group_key=? AND belief_key=? "
                   "AND valid_to IS NULL ORDER BY version DESC LIMIT 1", gkey, bkey)
    if last and last[0]["valid_from"] == at:
        return  # this evidence date is already recorded (idempotent on restart)
    if last and last[0]["valid_from"] > at:
        return
    v = 1
    if last:
        store.x("UPDATE beliefs SET valid_to=? WHERE group_key=? AND belief_key=? AND version=?", at, gkey, bkey,
                last[0]["version"])
        v = last[0]["version"] + 1
    store.x("INSERT INTO beliefs VALUES (?,?,?,?,?,?,?,?,?)", gkey, bkey, v, stmt, val, n, at, None, json.dumps(src))


def _timeline(c: Crust, group: dict, rules: dict) -> list[dict]:
    end = date.fromisoformat(rules["versions_at"][-1])
    out = []
    for i in range(int(rules["timeline_months"]) - 1, -1, -1):
        m_end = date(end.year, end.month, 1) - timedelta(days=1) if i else end
        for _ in range(i - 1):
            m_end = date(m_end.year, m_end.month, 1) - timedelta(days=1)
        m_start = date(m_end.year, m_end.month, 1)
        cur, past = "experience.employment_details.current", "experience.employment_details.past"
        j, _, _ = _count(c, group_conds(group, "current") + [_cond(f"{cur}.start_date", "=>", m_start.isoformat()),
                                                             _cond(f"{cur}.start_date", "=<", m_end.isoformat())])
        l, _, _ = _count(c, group_conds(group, "past") + [_cond(f"{past}.end_date", "=>", m_start.isoformat()),
                                                          _cond(f"{past}.end_date", "=<", m_end.isoformat())])
        out.append({"date": m_start.isoformat()[:7], "joiners": j, "leavers": l})
    return out
