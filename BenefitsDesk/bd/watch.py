"""Watch path for the cover-gap alarm. Watches are never the only path: the direct request uses the
same rule function (rules_engine.job_change) and the same action key, so both paths give one result
and one action.

Pull, don't trust the webhook: list the watch's runs, take finished runs after the last one processed,
read each run's delivered records, run the rule, prepare the action, THEN save the run id. A kill
before the save re-processes that run; the idempotency key makes the repeat a no-op.
"""
from __future__ import annotations

import json
import urllib.request

from . import actions, rules_engine as R
from .config import load_config
from .crust import Crust
from .facts import normalize_url
from .store import Store, h, now


def ensure_tables(store: Store) -> None:
    store.x("CREATE TABLE IF NOT EXISTS watches (watch_id TEXT PRIMARY KEY, persona_id TEXT, created_at TEXT)")


def register(store: Store, watch_id: str, profile_url: str) -> str:
    ensure_tables(store)
    pid = h(normalize_url(profile_url))
    if not store.q("SELECT 1 FROM personas WHERE persona_id=? AND consent=1", pid):
        raise ValueError("only an opted-in persona can be watched: run a request for this person first")
    store.x("INSERT OR REPLACE INTO watches VALUES (?,?,?)", str(watch_id), pid, now())
    return pid


def create(store: Store, c: Crust, profile_url: str) -> dict:
    """Entity watch on one opted-in person, firing only on a new employer (keys = company id)."""
    hook = (load_config().get("watch") or {}).get("webhook_url")
    if not hook:
        return {"created": False, "reason": "config.yaml watch.webhook_url is not set; Crustdata requires a "
                "notification channel. Runs can still be pulled for any existing watch with `bd watch-pull`."}
    body = {"entities": {"professional_network_profile_urls": [profile_url]},
            "track": {"field": "experience.employment_details.current", "type": "added",
                      "keys": ["crustdata_company_id", "name"]},
            "fields": ["experience"], "config": {"trigger": {"type": "interval", "every_hours": 24},
                                                  "max_results_per_run": 10},
            "notifications": [{"type": "webhook", "url": hook}]}
    r = c.call("/watch/person", body, cacheable=False)
    if not r.ok:
        return {"created": False, "reason": r.reason}
    wid = str((r.data or {}).get("id") or (r.data or {}).get("watch_id"))
    register(store, wid, profile_url)
    return {"created": True, "watch_id": wid}


def _records(summary: dict) -> list[dict]:
    out = []
    pd = summary.get("payload_delivery") or {}
    for n in summary.get("notifications") or []:
        payload = n.get("payload")
        if payload is None and pd.get("type") == "link" and pd.get("url"):
            with urllib.request.urlopen(pd["url"], timeout=20) as f:  # signed link, no auth header
                payload = {"notifications": [json.loads(line) for line in f.read().decode().splitlines() if line.strip()]}
        for rec in (payload or {}).get("notifications") or (payload or {}).get("results") or []:
            out.append(rec)
    return out


def pull(store: Store, c: Crust, watch_id: str, since: str, as_of: str, run_id: str) -> dict:
    ensure_tables(store)
    w = store.q("SELECT persona_id FROM watches WHERE watch_id=?", str(watch_id))
    if not w:
        return {"error": f"watch {watch_id} is not registered to an opted-in persona"}
    pid = w[0]["persona_id"]
    cur = store.q("SELECT last_run_id FROM watch_cursor WHERE watch_id=?", str(watch_id))
    last = int(cur[0]["last_run_id"]) if cur and cur[0]["last_run_id"] else 0
    r = c.call(f"/watch/person/{watch_id}/runs?limit=50", None, method="GET", cacheable=False)
    if not r.ok:
        return {"error": r.reason, "last_run_id": last}
    runs = sorted((r.data or {}).get("runs") or [], key=lambda x: x["id"])
    processed, alarms = [], []
    for run in runs:
        if run["id"] <= last:
            continue
        if run["status"] == "RUNNING":
            break  # finish later; do not move the cursor past an unfinished run
        if run["status"] == "SUCCESS" and run.get("new_records_count"):
            s = c.call(f"/watch/person/{watch_id}/runs/{run['id']}/summary", None, method="GET")
            if not s.ok:
                return {"error": s.reason, "last_run_id": last, "processed": processed}
            for rec in _records(s.data or {}):
                pd = rec.get("record") or {}
                a = R.job_change(pd, since, as_of, (s.data or {}).get("completed_at") or s.retrieved_at)
                a["via"] = f"watch {watch_id} run {run['id']} ({rec.get('uid')})"
                alarms.append(a)
                if a["status"] == "job_change":
                    payload = {"old_employer": a["old_employer"], "cover_end_date": a["cover_end_date"],
                               "convert_by": a["conversion_deadline"],
                               "request": "convert group health cover to a personal policy"}
                    actions.prepare(store, run_id, "conversion_request", pid,
                                    f"Ask the group insurer to convert cover from {a['old_employer']} to a personal "
                                    f"policy by {a['conversion_deadline']}", payload)
        store.x("INSERT OR REPLACE INTO watch_cursor VALUES (?,?,?)", str(watch_id), str(run["id"]), now())
        last = run["id"]
        processed.append(run["id"])
    return {"watch_id": watch_id, "processed_runs": processed, "last_run_id": last, "alarms": alarms}
