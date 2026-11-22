"""Local single-operator freight audit desk. All postings are internal simulations."""
import json
import os
import re
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from time import monotonic
from uuid import uuid4

from engine import run_case
from fx import assess
from intake import extract
from samples import sample

ROOT = Path(__file__).resolve().parent
# Accept plain KEY=value entries. Shell variables take precedence.
if (ROOT / ".env").is_file():
    for entry in (ROOT / ".env").read_text(encoding="utf-8-sig").splitlines():
        if entry.strip() and not entry.lstrip().startswith("#") and "=" in entry:
            key, value = entry.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip().strip(chr(34)).strip("'"))

MODE = os.getenv("FREIGHT_MODE", "mock").lower()
if MODE not in {"mock", "live"}:
    raise RuntimeError("FREIGHT_MODE must be mock or live")
class ServiceError(Exception):
    def __init__(self, status_code, detail):
        super().__init__(detail)
        self.status_code = status_code
        self.detail = detail


@contextmanager
def database(write=False):
    # Separate simulation runs from runs with live sources.
    path = os.getenv("FREIGHT_DB", str(ROOT / f"freight-{MODE}.sqlite3"))
    db = sqlite3.connect(path, timeout=30)
    try:
        db.execute("CREATE TABLE IF NOT EXISTS cases (id TEXT PRIMARY KEY, case_key TEXT UNIQUE, body TEXT NOT NULL)")
        db.execute("CREATE TABLE IF NOT EXISTS postings (invoice_key TEXT PRIMARY KEY, case_id TEXT NOT NULL, body TEXT NOT NULL)")
        db.execute("CREATE TABLE IF NOT EXISTS attempts (case_id TEXT, body TEXT NOT NULL)")
        if write:
            # Acquire lock before extraction, so concurrent replays spend and post once.
            db.execute("BEGIN IMMEDIATE")
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def get_case(db, rid):
    row = db.execute("SELECT body FROM cases WHERE id=?", (rid,)).fetchone()
    if not row:
        raise ServiceError(404, "Case not found")
    return json.loads(row[0])


def hold(record, step, reason, sources):
    record.update(status="REVIEW", payable_cents=0, recovered_cents=0, actions=[])
    record["trace"].append(dict(step=step, reason=reason, sources=sources))


def prepare_notice(actions, data, rid, trace):
    """Give the billing desk an actual notice to file with the settlement."""
    invoice = data["invoice_id"]
    lines = [f"Re: {invoice} / {data['po_id']}", "",
             f"The audit supports USD {actions[0]['amount_cents']/100:,.2f} "
             f"of USD {data['total_cents']/100:,.2f} invoiced."]
    for item in trace:
        if item["step"] in {"Price detention", "Price line haul"}:
            lines.append(item["reason"])
    lines.append(f"Internal settlement reference: {rid}.")
    for index, action in enumerate(actions, 1):
        action["entry_ref"] = f"{rid}-{index}"
        if action["type"] != "LEDGER_POST":
            action["notice_text"] = "\n".join(lines)


def process(db, packet, rid):
    start = monotonic()
    now = datetime.now(timezone.utc).isoformat()
    record = dict(id=rid, mode=MODE, packet=packet, extraction={}, trace=[], calls=[],
                  created_at=now, status="REVIEW", actions=[], payable_cents=0, recovered_cents=0)
    stage, sources = "Read invoice", ["packet.invoice_text"]
    try:
        raw = packet.get("invoice_text")
        if not isinstance(raw, str) or not raw.strip() or len(raw.encode()) > 6000:
            raise ValueError("Supply an invoice of 1 to 6,000 UTF-8 bytes")
        live = MODE == "live"
        call = dict(service="OpenAI" if live else "Fixture reader",
                    estimated_usd=None if live else 0, max_usd=0.003 if live else 0)
        record["calls"].append(call)
        data = extract(raw, MODE)
        record["extraction"] = data
        usage = data.get("usage") or {}
        if live and "prompt_tokens" in usage and "completion_tokens" in usage:
            call.update(usage=usage, estimated_usd=round((usage["prompt_tokens"]*0.15 +
                        usage["completion_tokens"]*0.60)/1_000_000, 8))
        note = packet.get("evidence_ref")
        result = run_case(packet, data, f"Reviewed delivery record {note}" if note else None)
        record.update(result)
        source_fields = {
            "Match purchase order": ["packet.po_id", "extraction.sources.po_id"],
            "Reconcile invoice": ["extraction.sources.base_cents", "extraction.sources.detention_cents", "extraction.sources.total_cents"],
            "Price line haul": ["packet.contracted_base_cents", "extraction.sources.base_cents"],
            "Price detention": ["packet.pod_minutes", "packet.free_minutes", "packet.detention_cents_per_hour", "extraction.sources.detention_cents"],
        }
        for decision in record["trace"]:
            if decision["step"] == "Settle in sandbox":
                decision["step"] = "Calculate proposed payable"
                decision["reason"] = "Subject to spending authority. " + decision["reason"]
            decision["sources"].extend(s for s in source_fields.get(decision["step"], []) if s not in decision["sources"])
        if record["status"] == "SETTLED":
            # These are candidate actions until checks and atomic commit succeed.
            proposed = record["actions"]
            record["actions"] = []
            stage, sources = "Check settlement authority", ["packet.invoice_date", "packet.cap_paise"]
            inv = data["invoice_id"].strip().casefold()
            prior = db.execute("SELECT case_id FROM postings WHERE invoice_key=?", (inv,)).fetchone()
            if prior:
                hold(record, "Duplicate invoice", "Invoice already posted under case " + prior[0],
                     ["extraction.invoice_id", "receipt:" + prior[0]])
            else:
                record["calls"].append(dict(service="Frankfurter" if live else "Fixture FX", estimated_usd=0, max_usd=0))
                fx = assess(record["payable_cents"], packet.get("invoice_date"), packet.get("cap_paise"), MODE)
                record["fx"] = fx
                if not fx["approved"]:
                    hold(record, stage, fx["reason"], fx["sources"])
                elif monotonic() - start > 25:
                    hold(record, "Time budget", "Run exceeded 25 seconds before posting", ["run.elapsed_ms"])
                else:
                    record["trace"].append(dict(step=stage, reason=fx["reason"], sources=fx["sources"]))
                    prepare_notice(proposed, data, rid, record["trace"])
                    db.execute("INSERT INTO postings VALUES (?,?,?)", (inv, rid, json.dumps(proposed)))
                    record["actions"] = proposed
                    record["trace"].append(dict(step="Post settlement", reason="Wrote one internal ledger entry and its remittance record together.", sources=["postings:" + rid]))
    except ValueError as exc:
        hold(record, stage, str(exc), sources)
    record["elapsed_ms"] = round((monotonic() - start) * 1000)
    db.execute("INSERT INTO cases VALUES (?,?,?) ON CONFLICT(id) DO UPDATE SET body=excluded.body",
               (rid, packet["case_id"], json.dumps(record)))
    db.execute("INSERT INTO attempts VALUES (?,?)", (rid, json.dumps(record)))
    return record


def get_sample(missing: bool = False):
    return {**sample(missing), "invoice_date":"2026-10-16", "cap_paise":30_000_000}


def run(payload: dict):
    packet = payload.get("packet")
    if not isinstance(packet, dict) or not isinstance(packet.get("case_id"), str) or not re.fullmatch(r"[A-Za-z0-9_-]{1,80}", packet["case_id"]):
        raise ServiceError(422, "Use a case ID of 1-80 letters, digits, underscores or hyphens")
    with database(True) as db:
        row = db.execute("SELECT body FROM cases WHERE case_key=?", (packet["case_id"],)).fetchone()
        if row:
            old = json.loads(row[0])
            if old["packet"] == packet:
                return old
            if old["status"] != "REVIEW":
                raise ServiceError(409, "Case already posted. A changed invoice needs a new case ID.")
            return process(db, packet, old["id"])
        return process(db, packet, uuid4().hex[:16])


def history():
    with database() as db:
        return [json.loads(row[0]) for row in db.execute("SELECT body FROM cases ORDER BY rowid DESC")]


def resolve(rid: str, payload: dict):
    minutes, ref = payload.get("pod_minutes"), payload.get("evidence_ref")
    if type(minutes) is not int or not 0 <= minutes <= 10080 or not isinstance(ref,str) or not 1 <= len(ref.strip()) <= 240:
        raise ServiceError(422, "Supply verified dwell minutes and a delivery-record reference")
    with database(True) as db:
        old = get_case(db, rid)
        if old["status"] != "REVIEW" or old["packet"].get("pod_minutes") is not None:
            raise ServiceError(409, "This case is not waiting for a missing delivery record")
        packet = {**old["packet"], "pod_minutes":minutes, "evidence_ref":ref.strip()}
        return process(db, packet, rid)


def retry(rid: str):
    with database(True) as db:
        old = get_case(db, rid)
        return old if old["status"] == "SETTLED" else process(db, old["packet"], rid)


def receipt_data(rid: str):
    with database() as db:
        current = get_case(db, rid)
        revisions = [json.loads(row[0]) for row in db.execute("SELECT body FROM attempts WHERE case_id=? ORDER BY rowid", (rid,))]
        return {**current, "attempts": revisions}
