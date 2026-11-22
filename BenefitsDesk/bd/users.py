"""People who use the guided flow: allowlist, PIN login, sessions, intake lookup, Forget me.

- Only profiles on config.yaml `consenting_personas` are ever looked up. Anything else: no call.
- The PIN is stored as a salted PBKDF2 hash. A wrong PIN, a locked account and an unknown first visit
  without consent all get the SAME message, so nothing is revealed about the person.
- This is demo sign-in, not identity proof (a production version would use Sign in with LinkedIn).
"""
from __future__ import annotations

import hashlib
import hmac
import json
import re
import secrets
from datetime import date, datetime, timedelta, timezone
from typing import Any

from .config import load_config, load_rules
from .crust import Crust
from .facts import normalize_url, person_entry
from .store import Store, h, now, state_dir

GENERIC = "Link or PIN not recognised. If this is your first visit, tick the box to agree to the lookup."
NOT_ALLOWED = "This demo only works for people who have agreed to be looked up. Nothing was looked up."

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (user_id TEXT PRIMARY KEY, profile_url TEXT, pin_salt TEXT, pin_hash TEXT,
  created_at TEXT, failed INTEGER DEFAULT 0, locked_until TEXT, mode TEXT);
CREATE TABLE IF NOT EXISTS sessions (token_hash TEXT PRIMARY KEY, user_id TEXT, created_at TEXT, expires_at TEXT);
CREATE TABLE IF NOT EXISTS user_state (user_id TEXT PRIMARY KEY, stage TEXT, intake TEXT, confirmed TEXT,
  answers TEXT, last_run_id TEXT, choice TEXT, updated_at TEXT);
CREATE TABLE IF NOT EXISTS user_runs (user_id TEXT, run_id TEXT, started TEXT, PRIMARY KEY (user_id, run_id));
CREATE TABLE IF NOT EXISTS persona_beliefs (persona_id TEXT, belief_key TEXT, version INTEGER, statement TEXT,
  value TEXT, label TEXT, source TEXT, valid_from TEXT, valid_to TEXT, trigger TEXT, last_checked TEXT,
  PRIMARY KEY (persona_id, belief_key, version));
CREATE TABLE IF NOT EXISTS persona_snapshots (persona_id TEXT, ts TEXT, run_id TEXT, gaps TEXT, next_step TEXT);
"""


class LoginError(Exception):
    def __init__(self, code: int, msg: str):
        super().__init__(msg)
        self.code, self.msg = code, msg


def ensure(store: Store) -> None:
    store.db.executescript(SCHEMA)


# ---- allowlist ----------------------------------------------------------------
def allowlisted(link: str | None = None, name: str | None = None, company: str | None = None) -> dict | None:
    for e in load_config().get("consenting_personas") or []:
        if link and normalize_url(link) == normalize_url(e["profile_url"]):
            return e
        if not link and name and company:
            if name.strip().lower() == e["name"].lower() and company.strip().lower() in [c.lower() for c in e.get("companies", [])]:
                return e
    return None


# ---- PIN --------------------------------------------------------------------
def _hash(pin: str, salt: str) -> str:
    it = int(load_config()["login"]["pin_iterations"])
    return hashlib.pbkdf2_hmac("sha256", pin.encode(), bytes.fromhex(salt), it).hex()


def _session(store: Store, uid: str) -> str:
    token = secrets.token_urlsafe(32)
    days = int(load_config()["login"]["session_days"])
    exp = (datetime.now(timezone.utc) + timedelta(days=days)).isoformat(timespec="seconds")
    store.x("INSERT INTO sessions VALUES (?,?,?,?)", hashlib.sha256(token.encode()).hexdigest(), uid, now(), exp)
    return token


def session_user(store: Store, token: str | None) -> str | None:
    if not token:
        return None
    ensure(store)
    r = store.q("SELECT user_id, expires_at FROM sessions WHERE token_hash=?", hashlib.sha256(token.encode()).hexdigest())
    if not r or r[0]["expires_at"] < now():
        return None
    return r[0]["user_id"]


def logout(store: Store, token: str | None) -> None:
    if token:
        store.x("DELETE FROM sessions WHERE token_hash=?", hashlib.sha256(token.encode()).hexdigest())


def state(store: Store, uid: str) -> dict:
    ensure(store)
    r = store.q("SELECT * FROM user_state WHERE user_id=?", uid)
    if not r:
        return {}
    d = dict(r[0])
    for k in ("intake", "confirmed", "answers", "choice"):
        d[k] = json.loads(d[k]) if d.get(k) else None
    return d


def save_state(store: Store, uid: str, **kw) -> None:
    ensure(store)
    cur = state(store, uid) or {"user_id": uid}
    cur.update(kw)
    store.x("INSERT OR REPLACE INTO user_state VALUES (?,?,?,?,?,?,?,?)", uid, cur.get("stage"),
            json.dumps(cur.get("intake")), json.dumps(cur.get("confirmed")), json.dumps(cur.get("answers")),
            cur.get("last_run_id"), json.dumps(cur.get("choice")), now())


def mode_of(store: Store, uid: str) -> str:
    ensure(store)
    r = store.q("SELECT mode FROM users WHERE user_id=?", uid)
    return (r[0]["mode"] if r and r[0]["mode"] else load_config()["guided"]["default_mode"])


def login(store: Store, link: str | None, name: str | None, company: str | None, pin: str, consent: bool,
          crust: Crust) -> tuple[dict, str]:
    """-> ({user_id, returning, stage}, session token). Raises LoginError."""
    ensure(store)
    if not re.fullmatch(r"\d{4}", pin or ""):
        raise LoginError(400, "The PIN is 4 digits.")
    entry = allowlisted(link, name, company)
    if entry is None:
        raise LoginError(403, NOT_ALLOWED)                     # no call is made
    uid = h(normalize_url(entry["profile_url"]))
    row = store.q("SELECT * FROM users WHERE user_id=?", uid)
    cfg = load_config()["login"]
    if row:
        u = row[0]
        if u["locked_until"] and u["locked_until"] > now():
            raise LoginError(401, GENERIC)
        if not hmac.compare_digest(_hash(pin, u["pin_salt"]), u["pin_hash"]):
            failed = (u["failed"] or 0) + 1
            lock = ((datetime.now(timezone.utc) + timedelta(minutes=int(cfg["lockout_minutes"]))).isoformat(timespec="seconds")
                    if failed >= int(cfg["max_failed_attempts"]) else None)
            store.x("UPDATE users SET failed=?, locked_until=? WHERE user_id=?", 0 if lock else failed, lock, uid)
            raise LoginError(401, GENERIC)
        store.x("UPDATE users SET failed=0, locked_until=NULL WHERE user_id=?", uid)
        st = state(store, uid)
        return {"user_id": uid, "returning": True, "stage": st.get("stage") or "confirm"}, _session(store, uid)
    if not consent:
        raise LoginError(401, GENERIC)                         # same words as a wrong PIN
    salt = secrets.token_hex(16)
    store.x("INSERT INTO users VALUES (?,?,?,?,?,?,?,?)", uid, entry["profile_url"], salt, _hash(pin, salt), now(), 0, None,
            load_config()["guided"]["default_mode"])
    store.x("INSERT OR IGNORE INTO personas VALUES (?,?,?,?,?)", uid, now(), 1, "{}", 1)
    items = intake(crust, entry, via_name=not link)
    save_state(store, uid, stage="confirm", intake=items)
    return {"user_id": uid, "returning": False, "stage": "confirm"}, _session(store, uid)


# ---- intake -----------------------------------------------------------------
AGE_BANDS = ["under-18", "18-24", "25-34", "35-44", "45-54", "55-64", "65+"]
CITY_CHOICES = ["Pilani", "Jaipur", "Delhi", "Noida", "Gurugram", "Bengaluru", "Mumbai"]


def enrich_body(url: str) -> dict:
    return {"professional_network_profile_urls": [url], "fields": ["basic_profile", "experience", "education"]}


def band_for(age: int) -> str:
    for b in AGE_BANDS[1:]:
        lo = int(b.split("-")[0].rstrip("+"))
        hi = int(b.split("-")[1]) if "-" in b else 200
        if lo <= age <= hi:
            return b
    return "under-18"


def _missing(key: str, label: str, question: str, choices: list[str] | None = None, why: str = "") -> dict:
    return {"key": key, "label": label, "value": None, "kind": "missing", "question": question,
            "choices": choices, "source": None, "basis": why}


def ask_everything(why: str) -> list[dict]:
    return [_missing("employer", "Where you work", "Where do you work now? Type 'none' if you are not working.", None, why),
            _missing("role", "Your job", "What is your job title?", None, why),
            _missing("start_date", "Started", "When did you start (month and year)?", None, why),
            _missing("city", "Your city", "Which city do you live in?", CITY_CHOICES, why),
            _missing("age_band", "Your age", "How old are you?", AGE_BANDS, why)]


def intake(c: Crust, entry: dict, via_name: bool = False) -> list[dict]:
    """One person lookup -> confirmation items (Checked / Guessed / missing). Never picks between lookalikes."""
    if via_name:
        r = c.call("/person/search", {"filters": {"op": "and", "conditions": [
            {"field": "basic_profile.name", "type": "=", "value": entry["name"]},
            {"op": "or", "conditions": [{"field": "experience.employment_details.current.company_name", "type": "in", "value": entry["companies"]},
                                        {"field": "experience.employment_details.past.company_name", "type": "in", "value": entry["companies"]}]}]},
            "limit": 3, "fields": ["basic_profile.name"]})
        rows = (r.data or {}).get("profiles") or [] if r.ok else []
        if len(rows) != 1:
            return ask_everything(f"name and company matched {len(rows)} people, so we did not pick one")
        e = c.call("/person/enrich", enrich_body(entry["profile_url"]))
        status, pd, _ = person_entry(e.data) if e.ok else ("error", None, "")
        if not pd or pd.get("crustdata_person_id") != rows[0].get("crustdata_person_id"):
            return ask_everything("the only name match is not the profile that agreed to be looked up")
        return _items(pd, e)
    e = c.call("/person/enrich", enrich_body(entry["profile_url"]))
    if not e.ok:
        return ask_everything(f"lookup not settled: {e.reason}")
    status, pd, _ = person_entry(e.data)
    if status == "redacted":
        return ask_everything("this record was removed at the person's request, so we use only your answers")
    if status != "matched":
        return ask_everything("no public record found")
    return _items(pd, e)


def _items(pd: dict, e) -> list[dict]:
    src = lambda path, rd=None: {"record": "crustdata /person/enrich", "record_id": str(pd.get("crustdata_person_id") or ""),
                                 "field_path": path, "record_date": rd, "retrieved_at": e.retrieved_at}
    ed = (pd.get("experience") or {}).get("employment_details") or {}
    cur = [(f"experience.employment_details.current[{i}]", j) for i, j in enumerate(ed.get("current") or [])]
    main = [(p, j) for p, j in cur if j.get("is_default")] or cur[:1]
    past = sorted([(f"experience.employment_details.past[{i}]", j) for i, j in enumerate(ed.get("past") or [])],
                  key=lambda pj: pj[1].get("end_date") or "", reverse=True)
    items: list[dict] = []
    job = main[0] if main else (past[0] if past else None)
    if job:
        p, j = job
        ended = (j.get("end_date") or "")[:10] if not main else None
        items.append({"key": "employer", "label": "Where you work" if main else "Your most recent job was at",
                      "value": j.get("name"), "kind": "checked", "source": src(f"{p}.name", (j.get("start_date") or "")[:10] or None),
                      "note": f"ended {ended}" if ended else None})
        items.append({"key": "role", "label": "Your job", "value": j.get("title"), "kind": "checked", "source": src(f"{p}.title")})
        items.append({"key": "start_date", "label": "Started", "value": (j.get("start_date") or "")[:10] or None,
                      "kind": "checked" if j.get("start_date") else "missing", "source": src(f"{p}.start_date")})
        if main:
            items.append({"key": "company_id", "label": "Employer record id", "value": j.get("crustdata_company_id"),
                          "kind": "checked", "source": src(f"{p}.crustdata_company_id"), "hidden": True})
        else:
            items.append({"key": "company_id", "label": "Employer record id", "value": j.get("crustdata_company_id"),
                          "kind": "checked", "source": src(f"{p}.crustdata_company_id"), "hidden": True})
    else:
        items += ask_everything("no job on the record")[:3]
    city = ((pd.get("basic_profile") or {}).get("location") or {}).get("city")
    items.append({"key": "city", "label": "Your city", "value": city, "kind": "checked", "source": src("basic_profile.location.city")}
                 if city else _missing("city", "Your city", "Which city do you live in?", CITY_CHOICES, "no city on the record"))
    ends = [(i, s.get("end_year")) for i, s in enumerate((pd.get("education") or {}).get("schools") or []) if s.get("end_year")]
    if ends:
        i, y = max(ends, key=lambda t: t[1])
        as_of = int(load_config()["guided"]["as_of"][:4])
        age = as_of - (int(y) - 22)
        items.append({"key": "age_band", "label": "Your age (our guess)", "value": band_for(age), "kind": "guessed",
                      "basis": f"education.schools[{i}].end_year = {y}; age estimated as {as_of} - ({y} - 22) = {age}",
                      "source": src(f"education.schools[{i}].end_year"), "choices": AGE_BANDS,
                      "question": "Our guess from your education dates. Please check it."})
    else:
        items.append(_missing("age_band", "Your age", "How old are you?", AGE_BANDS, "no education dates on the record"))
    return items


def confirm(store: Store, uid: str, decisions: dict) -> dict:
    """Each item is confirmed (keeps its label; a guessed age becomes Told) or edited (Told). The adults-only check
    runs on the CONFIRMED age only, never on the estimate."""
    st = state(store, uid)
    items = [i for i in st.get("intake") or []]
    out, missing = {}, []
    for it in items:
        if it.get("hidden"):
            out[it["key"]] = {"value": it["value"], "label": "checked", "source": it.get("source")}
            continue
        d = decisions.get(it["key"])
        if not d:
            missing.append(it["key"]); continue
        if d.get("action") == "confirm" and it["kind"] != "missing":
            label = "told" if it["key"] == "age_band" else it["kind"]
            out[it["key"]] = {"value": it["value"], "label": label, "source": it.get("source") if label != "told" else None,
                              "confirmed_from": it["kind"]}
        else:
            if d.get("value") in (None, ""):
                missing.append(it["key"]); continue
            out[it["key"]] = {"value": d["value"], "label": "told", "source": None, "edited_from": it.get("value")}
    if missing:
        raise LoginError(400, "Please confirm or change: " + ", ".join(missing))
    age = out.get("age_band", {}).get("value")
    if age in load_rules()["people"]["refuse_age_bands"]:
        save_state(store, uid, stage="refused", confirmed=out)
        return {"stage": "refused", "message": "This service is for adults only. Nothing more will be looked up."}
    save_state(store, uid, stage="questions", confirmed=out)
    return {"stage": "questions"}


# ---- forget -----------------------------------------------------------------
def forget(store: Store, uid: str) -> dict:
    ensure(store)
    run_ids = [r["run_id"] for r in store.q("SELECT run_id FROM user_runs WHERE user_id=?", uid)]
    url = (store.q("SELECT profile_url FROM users WHERE user_id=?", uid) or [{"profile_url": None}])[0]["profile_url"]
    counts: dict[str, int] = {}

    def rm(table: str, where: str, *args) -> None:
        n = store.q(f"SELECT COUNT(*) n FROM {table} WHERE {where}", *args)[0]["n"]
        store.x(f"DELETE FROM {table} WHERE {where}", *args)
        counts[table] = counts.get(table, 0) + n

    for t, col in (("users", "user_id"), ("sessions", "user_id"), ("user_state", "user_id"), ("user_runs", "user_id"),
                   ("persona_beliefs", "persona_id"), ("persona_snapshots", "persona_id"), ("facts", "persona_id"),
                   ("personas", "persona_id"), ("intents", "persona_id")):
        rm(t, f"{col}=?", uid)
    for rid in run_ids:
        for t in ("steps", "events", "runs"):
            rm(t, "run_id=?", rid)
        n = store.q("SELECT COUNT(*) n FROM ledger WHERE run_id=?", rid)[0]["n"]
        store.x("UPDATE ledger SET run_id='forgotten', note='' WHERE run_id=?", rid)   # keep the cost, drop the link
        counts["ledger_rows_unlinked"] = counts.get("ledger_rows_unlinked", 0) + n
    gone = 0
    if url:  # cached copies of this person's record
        for body in (enrich_body(url), {"professional_network_profile_urls": [url], "fields": ["basic_profile", "experience"]}):
            f = state_dir() / "cache" / f"{h('POST', '/person/enrich', body)}.json"
            if f.exists():
                f.unlink(); gone += 1
    counts["cached_records"] = gone
    return {"deleted": counts, "note": "Everything stored about you here is deleted. The cost ledger keeps no personal data. "
                                       "Anything already sent to the sandbox inbox stays there, as it would at an insurer."}
