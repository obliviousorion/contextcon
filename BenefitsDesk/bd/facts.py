"""Facts are pointers into records. Code copies the value out; an unresolved pointer is CANNOT VERIFY.

Also: persona sign-up (consent, adults only, dedupe on exact profile URL), the fact file from the
five answers (`told`) and the person record (`checked`), and `guessed` facts that may only choose
the next question.
"""
from __future__ import annotations

import json
import re
from datetime import date
from typing import Any

from .config import load_rules
from .store import Store, h, now

MISSING = object()


def resolve(doc: Any, path: str) -> Any:
    """'a.b[0].c' -> value, or MISSING. Never invents."""
    cur = doc
    for part in re.findall(r"[^.\[\]]+|\[\d+\]", path):
        if part.startswith("["):
            i = int(part[1:-1])
            if not isinstance(cur, list) or i >= len(cur):
                return MISSING
            cur = cur[i]
        else:
            if not isinstance(cur, dict) or part not in cur:
                return MISSING
            cur = cur[part]
    return cur


def checked(fact_id: str, statement: str, doc: Any, path: str, record: str, record_id: str,
            retrieved_at: str, record_date: str | None = None, url: str | None = None) -> dict:
    v = resolve(doc, path)
    if v is MISSING or v in (None, "", []):
        return {"fact_id": fact_id, "statement": statement, "value": None, "label": "checked",
                "cannot_verify": True, "missing": f"{record} has no value at {path}",
                "source": {"record": record, "record_id": record_id, "field_path": path,
                           "retrieved_at": retrieved_at, "record_date": record_date}}
    return {"fact_id": fact_id, "statement": statement.format(v=v), "value": v, "label": "checked",
            "source": {"record": record, "record_id": record_id, "field_path": path, "url": url,
                       "retrieved_at": retrieved_at, "record_date": record_date}}


def told(fact_id: str, statement: str, value: Any, at: str) -> dict:
    return {"fact_id": fact_id, "statement": statement.format(v=value), "value": value, "label": "told",
            "source": {"record": "the person's own answer", "field_path": f"answers.{fact_id}",
                       "retrieved_at": at, "record_date": at}}


def guessed(fact_id: str, statement: str, value: Any, basis: list[str], question: str) -> dict:
    return {"fact_id": fact_id, "statement": statement, "value": value, "label": "guessed",
            "source": None, "basis": basis, "question": question,
            "use": "chooses the next question only; never drives advice"}


# ---- persona ----------------------------------------------------------------
def normalize_url(url: str) -> str:
    u = (url or "").strip().lower().split("?")[0].split("#")[0].rstrip("/")
    u = re.sub(r"^https?://", "", u).replace("www.", "")
    return u


class Refused(Exception):
    def __init__(self, code: str, msg: str):
        super().__init__(msg)
        self.code, self.msg = code, msg


def sign_up(store: Store, persona: dict) -> dict:
    rules = load_rules()
    if not persona.get("consent"):
        raise Refused("NO_CONSENT", "The person has not opted in, so nothing is processed.")
    url = persona.get("profile_url")
    if not url:
        raise Refused("NEED_PROFILE_LINK", "A name alone can match several people. We never pick one: "
                      "please give your own profile link, or continue with your answers only.")
    band = (persona.get("answers") or {}).get("age_band")
    if band in rules["people"]["refuse_age_bands"]:
        raise Refused("UNDER_18", "This service is for adults only. Nothing was stored.")
    pid = h(normalize_url(url))
    row = store.q("SELECT signups FROM personas WHERE persona_id=?", pid)
    if row:  # duplicate sign-up: same exact identifier -> same persona
        store.x("UPDATE personas SET signups=signups+1, answers=? WHERE persona_id=?",
                json.dumps(persona.get("answers") or {}), pid)
        signups = row[0]["signups"] + 1
    else:
        store.x("INSERT INTO personas VALUES (?,?,?,?,?)", pid, now(), 1,
                json.dumps(persona.get("answers") or {}), 1)
        signups = 1
    return {"persona_id": pid, "signups": signups, "consent": True}


def forget(store: Store, persona_id: str) -> dict:
    n_f = store.q("SELECT COUNT(*) n FROM facts WHERE persona_id=?", persona_id)[0]["n"]
    store.x("DELETE FROM facts WHERE persona_id=?", persona_id)
    store.x("DELETE FROM personas WHERE persona_id=?", persona_id)
    store.x("DELETE FROM intents WHERE persona_id=? AND status='awaiting_approval'", persona_id)
    return {"persona_id": persona_id, "deleted_facts": n_f, "deleted_at": now(),
            "note": "Facts, answers and unapproved actions deleted. Cost ledger rows hold no personal data."}


def told_facts(answers: dict, at: str) -> list[dict]:
    out = []
    spec = [("age_band", "Age band: {v}"), ("dependants", "Dependants: {v}"), ("city", "City: {v}"),
            ("cover_held", "Cover already held: {v}"), ("monthly_budget_inr", "Monthly budget: Rs {v}"),
            ("role_group", "Staff group: {v}")]
    for k, tmpl in spec:
        if k in answers and answers[k] is not None:
            v = answers[k]
            out.append(told(k, tmpl if k != "cover_held" else "Cover already held: {v}",
                            ", ".join(v) if isinstance(v, list) and v else (v if v != [] else "none"), at)
                       | ({"value": v} if isinstance(v, list) else {}))
    return out


# ---- person record ------------------------------------------------------------
def person_entry(data: Any) -> tuple[str, dict | None, str]:
    """-> (match_status, person_data, base path)."""
    if not isinstance(data, list) or not data:
        return "not_found", None, ""
    item = data[0]
    status = item.get("match_status") or ("matched" if item.get("matches") else "not_found")
    if status == "redacted":
        return "redacted", None, ""
    m = item.get("matches") or []
    if not m:
        return "not_found", None, ""
    return "matched", m[0].get("person_data"), ""


def d(s: str | None) -> date | None:
    if not s:
        return None
    try:
        return date.fromisoformat(str(s)[:10])
    except ValueError:
        return None


def jobs(pd: dict) -> tuple[list[tuple[str, dict]], list[tuple[str, dict]]]:
    ed = ((pd or {}).get("experience") or {}).get("employment_details") or {}
    cur = [(f"experience.employment_details.current[{i}]", j) for i, j in enumerate(ed.get("current") or [])]
    past = [(f"experience.employment_details.past[{i}]", j) for i, j in enumerate(ed.get("past") or [])]
    return cur, past


def checked_facts(pd: dict, retrieved_at: str) -> tuple[list[dict], list[dict]]:
    """Facts from the person record + guessed facts (question-choosers only)."""
    rid = str(pd.get("crustdata_person_id") or "")
    rec = "crustdata /person/enrich"
    cur, past = jobs(pd)
    facts: list[dict] = []
    guesses: list[dict] = []
    main = [(p, j) for p, j in cur if j.get("is_default")] or (cur[:1] if len(cur) == 1 else [])
    if cur and not main:
        facts.append({"fact_id": "main_job", "statement": "Several current jobs and none marked as main",
                      "value": None, "label": "checked", "cannot_verify": True,
                      "missing": "is_default flag on one current job", "source": None})
    for p, j in main:
        rd = (j.get("start_date") or "")[:10] or None
        facts += [checked("current_employer", "Current employer: {v}", pd, f"{p}.name", rec, rid, retrieved_at, rd),
                  checked("current_employer_id", "Current employer id: {v}", pd, f"{p}.crustdata_company_id", rec, rid, retrieved_at, rd),
                  checked("current_title", "Current title: {v}", pd, f"{p}.title", rec, rid, retrieved_at, rd),
                  checked("current_start", "Started current job: {v}", pd, f"{p}.start_date", rec, rid, retrieved_at, rd)]
    if not cur:
        facts.append({"fact_id": "current_employer", "statement": "No current employer on the stored copy",
                      "value": None, "label": "checked",
                      "source": {"record": rec, "record_id": rid, "field_path": "experience.employment_details.current",
                                 "retrieved_at": retrieved_at, "record_date": None}})
    last = sorted(past, key=lambda pj: pj[1].get("end_date") or "", reverse=True)[:1]
    for p, j in last:
        rd = (j.get("end_date") or "")[:10] or None
        facts += [checked("last_past_employer", "Most recent past employer: {v}", pd, f"{p}.name", rec, rid, retrieved_at, rd),
                  checked("last_past_title", "Most recent past title: {v}", pd, f"{p}.title", rec, rid, retrieved_at, rd),
                  checked("last_past_type", "Employment type there: {v}", pd, f"{p}.employment_type", rec, rid, retrieved_at, rd),
                  checked("last_past_end", "Left that job: {v}", pd, f"{p}.end_date", rec, rid, retrieved_at, rd)]
        if (j.get("employment_type") or "").lower() in ("internship", "full-time", "contract"):
            guesses.append(guessed(
                "had_group_cover", f"May have had group health cover at {j.get('name')}", None,
                [f"{p}.employment_type"],
                f"Did your role at {j.get('name')} give you group health cover, and has it ended?"))
    loc = None
    for p, j in main or last:
        l = j.get("location")
        if isinstance(l, dict) and l.get("raw"):
            loc = (p, l["raw"])
    if loc:
        facts.append(checked("record_city", "Work location on record: {v}", pd, f"{loc[0]}.location.raw", rec, rid, retrieved_at))
    facts.append({"fact_id": "record_refresh_date", "statement": "Record refresh date: not provided by the source",
                  "value": None, "label": "checked", "cannot_verify": True,
                  "missing": "person_data.updated_at is empty, so 'no change since' cannot be verified",
                  "source": {"record": rec, "record_id": rid, "field_path": "updated_at", "retrieved_at": retrieved_at,
                             "record_date": None}})
    return facts, guesses


def conflicts(facts: list[dict]) -> list[dict]:
    """Told city vs checked work location: show both, ask, decide nothing on it."""
    by = {f["fact_id"]: f for f in facts}
    out = []
    t, c = by.get("city"), by.get("record_city")
    if t and c and c.get("value") and str(t["value"]).lower() not in str(c["value"]).lower():
        c["conflict"] = {"told": t["value"], "checked": c["value"]}
        out.append({"question": f"You said you live in {t['value']}; your record lists work in {c['value']}. Which is right for your cover?",
                    "why": "A told fact conflicts with a checked fact; we do not pick one."})
    return out
