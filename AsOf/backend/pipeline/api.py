"""AsOf pipeline API. Async functions called by the MCP server and the CLI."""
from __future__ import annotations

import hashlib
import inspect
import re
from datetime import date, datetime
from typing import Any

from backend.models import (AttestLine, Attestation, AuditReport, CaseFile, ClaimInput, ClaimVerdict, Entity,
                            Evidence, EvidenceRequest, ResolveResult)

from . import resolver, store
from .engine_adapter import config as engine_config, engine
from .errors import RequestError
from .session import Session, get_session, parse_ts, today

FIELDS = ("existence", "listing", "headcount", "revenue_band", "domains")
_SENT = re.compile(r"[^\w .,@:/-]")


def _sha(*parts: Any) -> str:
    return hashlib.sha256("|".join(str(p) for p in parts).encode()).hexdigest()


def _date(v: Any, what: str = "as_of") -> date:
    if isinstance(v, datetime):
        return v.date()
    if isinstance(v, date):
        return v
    try:
        return date.fromisoformat(str(v).strip())
    except Exception:
        raise RequestError(f"{what} must be a date like 2024-07-15, got {str(v)[:40]!r}") from None


def _field(v: Any) -> str:
    if not isinstance(v, str) or not v.strip():
        raise RequestError("a record type (field) is required: " + ", ".join(FIELDS))
    return v.strip().lower()


# ---- resolve --------------------------------------------------------------
async def resolve(name: str | None = None, domain: str | None = None) -> ResolveResult:
    return await resolver.resolve(get_session(), name=name, domain=domain)


def _refusal(field: str, as_of: date, code: str, missing: str, statement: str) -> AttestLine:
    return AttestLine(field=field, as_of=as_of, status="cannot_attest", statement=statement,
                      refusal_code=code, missing=missing)


def _unresolved_line(field: str, as_of: date, r: ResolveResult) -> AttestLine:
    return _refusal(field, as_of, "CANNOT_RESOLVE", r.missing or "a domain",
                    f"CANNOT ATTEST: company not resolved; missing {r.missing or 'a domain'}.")


async def _attest_one(s: Session, entity: Entity, field: str, as_of: date, prefix: str):
    """-> (line, subsequent, evidence). Never raises on source trouble."""
    if field not in FIELDS:
        return (_refusal(field, as_of, "NO_RECORD_TYPE", f"a supported record type ({', '.join(FIELDS)})",
                         f"CANNOT ATTEST: '{_SENT.sub('', field)[:40]}' is not a record type AsOf attests."), [], [])
    rec, failed = await s.fetch_record(entity.crustdata_company_id)
    if rec is None:
        held = failed is not None and failed.kind == "held"
        code = "BUDGET_HELD" if held else "SOURCE_UNAVAILABLE"
        why = failed.reason if failed is not None else "unknown"
        return (_refusal(field, as_of, code, "a reachable source" if not held else "a raised credit or time limit",
                         f"CANNOT ATTEST: source returned no usable record ({why})."), [], [])
    try:
        line, subsequent, evidence = engine().attest(rec.data, field, as_of, rec.retrieved_at, engine_config(),
                                                     evidence_prefix=prefix)
    except Exception as e:  # engine bug must not become an answer
        return (_refusal(field, as_of, "SOURCE_UNAVAILABLE", "a well-formed record",
                         f"CANNOT ATTEST: record could not be evaluated ({type(e).__name__})."), [], [])
    for ev in evidence:
        if ev.cache_key is None:
            ev.cache_key = rec.cache_key
    return line, list(subsequent), list(evidence)


async def attest_full(domain: str, field: str, as_of) -> tuple[AttestLine, list[AttestLine], dict[str, Evidence]]:
    s = get_session()
    field, d = _field(field), _date(as_of)
    r = await resolver.resolve(s, domain=domain)
    if r.status != "resolved":
        return _unresolved_line(field, d, r), [], {}
    line, sub, evs = await _attest_one(s, r.entity, field, d, "E")
    return line, sub, {e.id: e for e in evs}


async def attest(domain: str, field: str, as_of) -> AttestLine:
    return (await attest_full(domain, field, as_of))[0]


async def observe(domain: str, field: str, d1, d2) -> tuple[AttestLine, AttestLine]:
    """Two dated lines side by side. Never a growth or ratio verdict."""
    s = get_session()
    field, a, b = _field(field), _date(d1, "d1"), _date(d2, "d2")
    r = await resolver.resolve(s, domain=domain)
    if r.status != "resolved":
        return _unresolved_line(field, a, r), _unresolved_line(field, b, r)
    if field not in FIELDS:
        return (await _attest_one(s, r.entity, field, a, "E"))[0], (await _attest_one(s, r.entity, field, b, "E"))[0]
    rec, failed = await s.fetch_record(r.entity.crustdata_company_id)
    if rec is None:
        why = failed.reason if failed else "unknown"
        mk = lambda dd: _refusal(field, dd, "SOURCE_UNAVAILABLE", "a reachable source",  # noqa: E731
                                 f"CANNOT ATTEST: source returned no usable record ({why}).")
        return mk(a), mk(b)
    return engine().observe(rec.data, field, a, b, rec.retrieved_at, engine_config())


# ---- case files -------------------------------------------------------------
def _renumber(parts: list[tuple[AttestLine, list[AttestLine], list[Evidence]]],
              base: dict[str, Evidence]) -> dict[str, Evidence]:
    """Globally renumber evidence E{n} across fields; base evidence (identification) keeps E1."""
    out = dict(base)
    n = len(out)
    for line, subs, evs in parts:
        mapping: dict[str, str] = {}
        for ev in evs:
            n += 1
            mapping[ev.id] = f"E{n}"
            out[f"E{n}"] = ev.model_copy(update={"id": f"E{n}"})
        for ln in [line, *subs]:
            ln.evidence_ids = [mapping.get(e, e) for e in ln.evidence_ids]
    return out


def _entity_evidence(s: Session, ent: Entity) -> dict[str, Evidence]:
    ev = s.entity_evidence.get(ent.crustdata_company_id)
    when = parse_ts(ev.get("retrieved_at")) if ev else None
    if not ev or when is None:
        ent.evidence_id = None
        return {}
    return {"E1": Evidence(id="E1", kind="company_record", source_endpoint=ev["source_endpoint"],
                           field_path=ev["field_path"], excerpt=ev["excerpt"], retrieved_at=when,
                           cache_key=ev.get("cache_key"))}


def _needs_evidence_request(lines: list[AttestLine]) -> list[str]:
    items: list[str] = []
    by = {ln.field: ln for ln in lines}
    ex, hc = by.get("existence"), by.get("headcount")
    if ex is not None and ex.status != "attested":
        items.append("registration documents (GSTIN or CIN, incorporation year)")
    if hc is not None and hc.status != "attested":
        items.append("a dated headcount statement (payroll summary or filing)")
    return items


async def _case(kind: str, domain: str, as_of: date) -> CaseFile:
    s = get_session()
    mark = s.ledger_mark()
    dom = resolver.normalize_domain(domain)
    r = await resolver.resolve(s, domain=dom)
    request = {"tool": "clear_counterparty" if kind == "clearance" else "dispute_file",
               "domain": dom, "as_of": as_of.isoformat()}
    cid = r.entity.crustdata_company_id if r.entity else "unresolved"
    key = _sha(kind, cid if r.entity else dom, as_of, ",".join(FIELDS))
    if r.status != "resolved":
        er = _evidence_request(dom, ["the company's domain", "registration documents (GSTIN or CIN)"])
        cf = CaseFile(id="CF-" + key[:12], kind=kind, request=request, resolve=r, evidence_request=er,
                      cost=s.cost_since(mark), idempotency_key=key)
        store.save(er)
        store.save(cf)
        return cf
    base = _entity_evidence(s, r.entity)
    parts = [await _attest_one(s, r.entity, f, as_of, f"L{i}_") for i, f in enumerate(FIELDS)]
    evidence = _renumber(parts, base)
    lines = [p[0] for p in parts]
    flat_subs = [x for p in parts for x in p[1]]
    att = Attestation(entity=r.entity, as_of=as_of, lines=lines, subsequent_events=flat_subs,
                      generated_at=datetime.now().astimezone())
    missing = _needs_evidence_request(lines)
    er = _evidence_request(dom, missing) if missing else None
    cf = CaseFile(id="CF-" + key[:12], kind=kind, request=request, resolve=r, attestation=att,
                  evidence=evidence, evidence_request=er, cost=s.cost_since(mark), idempotency_key=key)
    if er:
        store.save(er)
    store.save(cf)
    return cf


async def clear_counterparty(domain: str) -> CaseFile:
    return await _case("clearance", domain, today())


async def dispute_file(domain: str, as_of) -> CaseFile:
    d = _date(as_of)
    if d > today():
        raise RequestError("a dispute file needs a past date; use clear_counterparty for today")
    return await _case("dispute", domain, d)


# ---- audit --------------------------------------------------------------------
async def audit_claims(domain: str, claims: list[ClaimInput | dict]) -> AuditReport:
    s = get_session()
    if not isinstance(claims, list) or not claims:
        raise RequestError("give at least one structured claim: {id, text, field, value, as_of}")
    try:
        cl = [c if isinstance(c, ClaimInput) else ClaimInput.model_validate(c) for c in claims]
    except Exception:
        raise RequestError("claims must be structured: {id, text, field, value, as_of}") from None
    r = await resolver.resolve(s, domain=domain)
    key = _sha("audit", r.entity.crustdata_company_id if r.entity else domain,
               ";".join(f"{c.id}:{c.field}:{c.value}:{c.as_of}" for c in cl))
    verdicts: list[ClaimVerdict] = []
    rec = failed = None
    if r.status == "resolved":
        rec, failed = await s.fetch_record(r.entity.crustdata_company_id)
    for c in cl:
        d = c.as_of or today()
        if r.status != "resolved":
            ln = _unresolved_line(c.field, d, r)
            verdicts.append(ClaimVerdict(claim_id=c.id, verdict="cannot_verify", line=ln,
                                         reason=f"Cannot verify: company not resolved; missing {r.missing}."))
        elif rec is None:
            ln = _refusal(c.field, d, "SOURCE_UNAVAILABLE", "a reachable source",
                          f"CANNOT ATTEST: source returned no usable record ({failed.reason if failed else '?'}).")
            verdicts.append(ClaimVerdict(claim_id=c.id, verdict="cannot_verify", line=ln,
                                         reason="Cannot verify: source unavailable."))
        else:
            verdicts.append(engine().audit_claim(rec.data, c, rec.retrieved_at, engine_config()))
    rep = AuditReport(id="AR-" + key[:12], entity=r.entity, verdicts=verdicts, idempotency_key=key)
    store.save(rep)
    return rep


# ---- evidence request -----------------------------------------------------------
def _evidence_request(target: str, items: list[str]) -> EvidenceRequest:
    return EvidenceRequest(target=target, items=items, idempotency_key=_sha("evidence", target, sorted(items)))


async def request_evidence(target: str, items: list[str]) -> EvidenceRequest:
    if not isinstance(target, str) or not target.strip():
        raise RequestError("a target (domain or company name) is required")
    if not isinstance(items, list):
        raise RequestError("items must be a list of what is needed, e.g. ['GSTIN']")
    clean = [i.strip()[:120] for i in items if isinstance(i, str) and i.strip()]
    if not clean:
        raise RequestError("name at least one item needed from the counterparty")
    er = _evidence_request(target.strip()[:200], clean)
    store.save(er)
    return er


# ---- approval and issue (thin hooks into the platform) -----------------------------
def _platform():
    try:
        from backend.platform import actions
        return actions
    except Exception:
        return None


async def _maybe(v):
    return await v if inspect.isawaitable(v) else v


def _status_of(res: Any) -> str | None:
    if isinstance(res, dict):
        return res.get("status")
    return getattr(res, "status", None)


_ACTION = {"CaseFile": "issue_case_file", "AuditReport": "issue_audit_report",
           "EvidenceRequest": "send_evidence_request"}


async def approve(artifact_id: str) -> dict:
    """Records the person's approval in the platform (one transition; a double click is a no-op)."""
    obj = store.load(artifact_id)
    plat = _platform()
    if plat is None:
        return {"id": artifact_id, "status": "held_for_approval", "note": "platform not installed; nothing approved"}
    first = bool(await _maybe(plat.approve(obj.idempotency_key)))
    if hasattr(obj, "status") and obj.status == "draft":
        obj.status = "approved"
        store.save(obj)
    return {"id": artifact_id, "status": "approved", "first_approval": first}


async def issue(artifact_id: str) -> dict:
    """Goes through platform.actions: held until approved, sandbox-only, exactly once per key."""
    obj = store.load(artifact_id)
    plat = _platform()
    action = _ACTION[type(obj).__name__]
    if plat is None:
        return {"id": artifact_id, "status": "held_for_approval", "note": "platform not installed; nothing sent"}
    payload = {"id": artifact_id, "type": type(obj).__name__, "idempotency_key": obj.idempotency_key,
               "body": obj.model_dump(mode="json")}
    rec = plat.execute_approved(obj.idempotency_key, action, artifact_id, lambda: plat.sandbox_send(payload))
    if rec is None:
        return {"id": artifact_id, "action": action, "status": "held_for_approval",
                "note": "run approve first; nothing was sent"}
    if rec.status == "done" and hasattr(obj, "status"):
        obj.status = "sent_sandbox" if isinstance(obj, EvidenceRequest) else "issued_sandbox"
        store.save(obj)
    return {"id": artifact_id, "action": action, "status": rec.status, "key": rec.key}


def _jsonable(v: Any) -> Any:
    if hasattr(v, "model_dump"):
        return v.model_dump(mode="json")
    return v if isinstance(v, (dict, list, str, int, float, bool, type(None))) else str(v)


async def watch(domain: str) -> dict:
    """Creates a held watcher request (create_watcher needs approval). Alerts cost 5 credits each."""
    s = get_session()
    r = await resolver.resolve(s, domain=domain)
    if r.status != "resolved":
        return {"status": "cannot_resolve", "missing": r.missing}
    try:
        from backend.platform import watchers
    except Exception:
        return {"status": "held_for_approval", "note": "watchers module not installed; nothing created"}
    return _jsonable(watchers.create(resolver.normalize_domain(domain), r.entity.crustdata_company_id))
