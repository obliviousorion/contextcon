"""Minimal stand-in for backend.engine until it lands. Same signatures; deliberately simple."""
from __future__ import annotations

from datetime import date, datetime
from types import SimpleNamespace

from backend.models import AttestLine, ClaimInput, ClaimVerdict, Evidence


def load_config(path):
    return {}


def _ev(prefix, n, path, excerpt, point, ts):
    return Evidence(id=f"{prefix}{n}", kind="company_record", source_endpoint="/company/enrich", field_path=path,
                    excerpt=str(excerpt)[:400], point_date=point, retrieved_at=ts)


def attest(record, field, as_of, retrieved_at, config, evidence_prefix="E"):
    ts = retrieved_at if isinstance(retrieved_at, datetime) else datetime.fromisoformat(retrieved_at)
    mk = lambda **k: AttestLine(field=field, as_of=as_of, **k)  # noqa: E731
    if field == "existence":
        y = (record.get("basic_info") or {}).get("year_founded")
        if y is None:
            return mk(status="cannot_attest", statement="CANNOT ATTEST", refusal_code="CANNOT_ATTEST", missing="year_founded"), [], []
        e = _ev(evidence_prefix, 1, "basic_info.year_founded", y, None, ts)
        return mk(status="attested", value=y, statement=f"stored copy retrieved {ts}; founded {y}", evidence_ids=[e.id]), [], [e]
    if field == "headcount":
        pts = (record.get("headcount") or {}).get("timeseries") or []
        before = [p for p in pts if date.fromisoformat(p["date"]) <= as_of]
        if not before:
            first = pts[0]["date"] if pts else "n/a"
            return mk(status="cannot_attest", statement="CANNOT ATTEST", refusal_code="NOT_YET_RECORDED", missing=f"first point {first}"), [], []
        p = before[-1]
        e = _ev(evidence_prefix, 1, f"headcount.timeseries[{p['date']}].employee_count", p["employee_count"], date.fromisoformat(p["date"]), ts)
        return mk(status="attested", value=p["employee_count"], point_date=e.point_date, label="profile-derived count",
                  statement=f"Data point dated {p['date']} states {p['employee_count']}; stored copy retrieved {ts}.", evidence_ids=[e.id]), [], [e]
    if field == "domains":
        d = (record.get("basic_info") or {}).get("all_domains") or []
        e = _ev(evidence_prefix, 1, "basic_info.all_domains", d, None, ts)
        return mk(status="attested", value=d, label="true at retrieval only", statement="domains at retrieval", evidence_ids=[e.id]), [], [e]
    return mk(status="cannot_attest", statement="CANNOT ATTEST", refusal_code="NOT_YET_RECORDED", missing=f"fake engine: {field}"), [], []


def observe(record, field, d1, d2, retrieved_at, config):
    return attest(record, field, d1, retrieved_at, config)[0], attest(record, field, d2, retrieved_at, config)[0]


def audit_claim(record, claim: ClaimInput, retrieved_at, config):
    ln = attest(record, claim.field, claim.as_of or date.today(), retrieved_at, config)[0]
    return ClaimVerdict(claim_id=claim.id, verdict="cannot_verify", line=ln, reason="fake: cannot verify")


FAKE = SimpleNamespace(load_config=load_config, attest=attest, observe=observe, audit_claim=audit_claim)
