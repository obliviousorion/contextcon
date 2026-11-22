"""AsOf pipeline API. Async functions called by the MCP server and the CLI."""
from __future__ import annotations

import hashlib
import inspect
import os
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


def _bind(s: Session, tool: str, *parts: Any) -> None:
    s.use_run("rq-" + _sha(tool, *parts)[:20])


# ---- resolve --------------------------------------------------------------
async def resolve(name: str | None = None, domain: str | None = None) -> ResolveResult:
    s = get_session()
    _bind(s, "resolve", (domain or "").strip().lower(), (name or "").strip().lower())
    return await resolver.resolve(s, name=name, domain=domain)


def _refusal(field: str, as_of: date, code: str, missing: str, statement: str) -> AttestLine:
    return AttestLine(field=field, as_of=as_of, status="cannot_attest", statement=statement,
                      refusal_code=code, missing=missing)


def _unresolved_line(field: str, as_of: date, r: ResolveResult) -> AttestLine:
    return _refusal(field, as_of, "CANNOT_RESOLVE", r.missing or "a domain",
                    f"CANNOT ATTEST: company not resolved; missing {r.missing or 'a domain'}.")


def _attest_sync(rec, field: str, as_of: date, prefix: str):
    """Pure engine call on a fetched record. Never raises."""
    try:
        line, subsequent, evidence = engine().attest(rec["data"], field, as_of, rec["retrieved_at"], engine_config(),
                                                     evidence_prefix=prefix)
    except Exception as e:  # engine bug must not become an answer
        return (_refusal(field, as_of, "SOURCE_UNAVAILABLE", "a well-formed record",
                         f"CANNOT ATTEST: record could not be evaluated ({type(e).__name__})."), [], [])
    for ev in evidence:
        if ev.cache_key is None:
            ev.cache_key = rec["cache_key"]
    return line, list(subsequent), list(evidence)


def _no_record(field: str, as_of: date, failed) -> AttestLine:
    held = failed is not None and failed.kind == "held"
    code = "BUDGET_HELD" if held else "SOURCE_UNAVAILABLE"
    why = failed.reason if failed is not None else "unknown"
    return _refusal(field, as_of, code, "a raised credit or time limit" if held else "a reachable source",
                    f"CANNOT ATTEST: source returned no usable record ({why}).")


async def _attest_one(s: Session, entity: Entity, field: str, as_of: date, prefix: str):
    """-> (line, subsequent, evidence). Never raises on source trouble."""
    if field not in FIELDS:
        return (_refusal(field, as_of, "NO_RECORD_TYPE", f"a supported record type ({', '.join(FIELDS)})",
                         f"CANNOT ATTEST: '{_SENT.sub('', field)[:40]}' is not a record type AsOf attests."), [], [])
    rec, failed = await s.fetch_record(entity.crustdata_company_id)
    if rec is None:
        return _no_record(field, as_of, failed), [], []
    return _attest_sync({"data": rec.data, "retrieved_at": rec.retrieved_at, "cache_key": rec.cache_key},
                        field, as_of, prefix)


async def attest_full(domain: str, field: str, as_of) -> tuple[AttestLine, list[AttestLine], dict[str, Evidence]]:
    s = get_session()
    field, d = _field(field), _date(as_of)
    _bind(s, "attest", str(domain).strip().lower(), field, d)
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
    _bind(s, "observe", str(domain).strip().lower(), field, a, b)
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


class _StepFailed(Exception):
    def __init__(self, code: str, why: str, resolve: ResolveResult | None = None):
        self.code, self.why, self.resolve = code, why, resolve


def _entity_ev_from(s: Session, ent: Entity, ev: dict | None) -> dict[str, Evidence]:
    if ev:
        s.entity_evidence[ent.crustdata_company_id] = ev
    return _entity_evidence(s, ent)


def _assemble(s: Session, kind: str, dom: str, as_of: date, steps: dict, fail: _StepFailed | None,
              mark: int, served0: dict) -> CaseFile:
    request = {"tool": "clear_counterparty" if kind == "clearance" else "dispute_file",
               "domain": dom, "as_of": as_of.isoformat()}
    rs = steps.get("resolve")
    r = ResolveResult.model_validate(rs["resolve"]) if rs else (
        fail.resolve if fail and fail.resolve else ResolveResult(
            status="cannot_resolve", missing=f"a raised credit or time limit ({fail.code}: {fail.why})" if fail else "a domain"))
    resumed = {"identify": 0, "enrich": 0}
    for st in steps.values():
        for k in resumed:
            resumed[k] += int(st.get(f"served_{k}", 0)) if isinstance(st, dict) else 0
    cid = r.entity.crustdata_company_id if r.status == "resolved" and r.entity else None
    key = _sha(kind, cid if cid else dom, as_of, ",".join(FIELDS))
    # recorded cost comes from the step outputs, so a resumed run reports the same figure
    cost = lambda: s.cost_since(mark, s.served_mark(), resumed)  # noqa: E731
    if cid is None:
        er = _evidence_request(dom, ["the company's domain", "registration documents (GSTIN or CIN)"])
        cf = CaseFile(id="CF-" + key[:12], kind=kind, request=request, resolve=r, evidence_request=er,
                      cost=cost(), idempotency_key=key)
        store.save(er)
        store.save(cf)
        return cf
    base = _entity_ev_from(s, r.entity, rs.get("ev"))
    parts = []
    for i, f in enumerate(FIELDS):
        st = steps.get(f"attest_{f}")
        if st is None:
            code = fail.code if fail else "BUDGET_HELD"
            why = fail.why if fail else "run held before this step"
            parts.append((_refusal(f, as_of, code, "a raised credit or time limit" if code == "BUDGET_HELD"
                                   else "a reachable source", f"CANNOT ATTEST: {why}."), [], []))
        else:
            parts.append((AttestLine.model_validate(st["line"]), [AttestLine.model_validate(x) for x in st["subs"]],
                          [Evidence.model_validate(x) for x in st["evidence"]]))
    evidence = _renumber(parts, base)
    lines = [p[0] for p in parts]
    flat_subs = [x for p in parts for x in p[1]]
    att = Attestation(entity=r.entity, as_of=as_of, lines=lines, subsequent_events=flat_subs,
                      generated_at=datetime.now().astimezone())
    missing = _needs_evidence_request(lines)
    er = _evidence_request(dom, missing) if missing else None
    cf = CaseFile(id="CF-" + key[:12], kind=kind, request=request, resolve=r, attestation=att,
                  evidence=evidence, evidence_request=er, cost=cost(), idempotency_key=key)
    if er:
        store.save(er)
    store.save(cf)
    return cf


async def _case(kind: str, domain: str, as_of: date) -> CaseFile:
    """resolve -> fetch record -> attest per field -> assemble, as resumable runstate steps."""
    import asyncio
    from backend.platform import runstate

    s = get_session()
    dom = resolver.normalize_domain(domain)
    run_id = "cf-" + _sha(kind, dom, as_of, ",".join(FIELDS))[:20]
    s.use_run(run_id)  # same ledger file for the same request, across kill and restart
    mark, served0 = s.ledger_mark(), s.served_mark()
    loop = asyncio.get_running_loop()
    call = lambda coro: asyncio.run_coroutine_threadsafe(coro, loop).result()  # noqa: E731

    def step_resolve(_):
        before = s.served_mark()
        r = call(resolver.resolve(s, domain=dom))
        if r.status != "resolved" and (r.missing or "").startswith("a reachable source"):
            raise _StepFailed("SOURCE_UNAVAILABLE", r.missing, r)  # transient: not persisted, retried on resume
        ent = r.entity
        return {"resolve": r.model_dump(mode="json"), "served_identify": s.served["identify"] - before["identify"],
                "ev": s.entity_evidence.get(ent.crustdata_company_id) if ent else None}

    def step_fetch(res):
        if res["resolve"]["resolve"]["status"] != "resolved":
            return {"skipped": True}
        cid = res["resolve"]["resolve"]["entity"]["crustdata_company_id"]
        before = s.served["enrich"]
        rec, failed = call(s.fetch_record(cid))
        if rec is None:
            raise _StepFailed("BUDGET_HELD" if failed is not None and failed.kind == "held" else "SOURCE_UNAVAILABLE",
                              failed.reason if failed is not None else "no record")
        return {"data": rec.data, "retrieved_at": rec.retrieved_at.isoformat(), "cache_key": rec.cache_key,
                "served_enrich": s.served["enrich"] - before}

    def mk_attest(i, f):
        def step(res):
            fe = res["fetch"]
            if fe.get("skipped"):
                return {"skipped": True}
            rec = {"data": fe["data"], "retrieved_at": parse_ts(fe["retrieved_at"]), "cache_key": fe["cache_key"]}
            line, subs, evs = _attest_sync(rec, f, as_of, f"L{i}_")
            return {"line": line.model_dump(mode="json"), "subs": [x.model_dump(mode="json") for x in subs],
                    "evidence": [e.model_dump(mode="json") for e in evs]}
        return step

    steps = [("resolve", step_resolve), ("fetch", step_fetch)] + [(f"attest_{f}", mk_attest(i, f))
                                                                  for i, f in enumerate(FIELDS)]
    fail = None
    try:
        res = await asyncio.to_thread(runstate.run, run_id, steps, cost_fn=lambda: s.client.ledger.total)
        done = res.results
        if res.status == "BUDGET_HELD":
            fail = _StepFailed("BUDGET_HELD", res.held_reason or "limit reached")
    except _StepFailed as e:
        fail = e
        done = runstate.load_state(run_id)[0]["steps"]
    done = {k: v for k, v in done.items() if not (k != "resolve" and isinstance(v, dict) and v.get("skipped"))}
    if done.get("resolve", {}).get("resolve", {}).get("status") == "cannot_resolve":
        done = {"resolve": done["resolve"]}
    return _assemble(s, kind, dom, as_of, done, fail, mark, served0)


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
    _bind(s, "audit", str(domain).strip().lower(), ";".join(f"{c.id}:{c.field}:{c.value}:{c.as_of}" for c in cl))
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


def _approver(by: str | None) -> str:
    return (by or os.environ.get("USER") or "unknown")[:80]


def _is_watch(i: str) -> bool:
    return isinstance(i, str) and i.startswith("watch:")


async def approve(artifact_id: str, by: str | None = None) -> dict:
    """Human approval (CLI only). Records who and when; refuses unless the artifact is still a draft."""
    plat = _platform()
    who, at = _approver(by), datetime.now().astimezone().isoformat()
    if _is_watch(artifact_id):
        if _watch_entry(artifact_id) is None:
            raise RequestError(f"no held watcher {artifact_id!r}; run watch first")
        if store.meta_load(artifact_id).get("approval"):
            raise RequestError(f"{artifact_id} was already approved; nothing to do")
        key = artifact_id
    else:
        obj = store.load(artifact_id)
        if getattr(obj, "status", "draft") != "draft" or store.meta_load(artifact_id).get("approval"):
            raise RequestError(f"{artifact_id} is no longer a draft (status {obj.status}); approval refused")
        key = obj.idempotency_key
    if plat is None:
        return {"id": artifact_id, "status": "held_for_approval", "note": "platform not installed; nothing approved"}
    first = bool(await _maybe(plat.approve(key)))
    store.meta_update(artifact_id, approval={"by": who, "at": at})
    if not _is_watch(artifact_id):
        obj.status = "approved"
        store.save(obj)
    return {"id": artifact_id, "status": "approved", "first_approval": first, "approved_by": who, "approved_at": at}


async def issue(artifact_id: str) -> dict:
    """Goes through platform.actions: held until approved, sandbox-only, exactly once per key."""
    if _is_watch(artifact_id):
        return await _issue_watch(artifact_id)
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


def _watchers():
    try:
        from backend.platform import watchers
        return watchers
    except Exception:
        return None


def _watch_entry(key: str) -> dict | None:
    w = _watchers()
    return w._registry().get(key) if w is not None else None


def _watch_by_id(ident: str) -> tuple[str, dict] | None:
    w = _watchers()
    if w is None:
        return None
    for k, e in w._registry().items():
        if ident in (k, e.get("watch_id")):
            return k, e
    return None


async def watch(domain: str) -> dict:
    """Creates a held watcher request (create_watcher needs approval). Alerts cost 5 credits each."""
    s = get_session()
    r = await resolver.resolve(s, domain=domain)
    if r.status != "resolved":
        return {"status": "cannot_resolve", "missing": r.missing}
    w = _watchers()
    if w is None:
        return {"status": "held_for_approval", "note": "watchers module not installed; nothing created"}
    ent = _jsonable(w.create(resolver.normalize_domain(domain), r.entity.crustdata_company_id))
    ent["watch_id_handle"] = ent["key"]
    ent["next"] = f"approve {ent['key']}, then issue {ent['key']}"
    return ent


async def _issue_watch(key: str) -> dict:
    w = _watchers()
    ent = _watch_entry(key)
    if w is None or ent is None:
        raise RequestError(f"no held watcher {key!r}; run watch first")
    s = get_session()

    def create_fn():
        if s.client.mode != "replay":
            raise RequestError("live watcher creation is not wired in the pipeline; use replay")
        return "w-" + key.split(":", 1)[-1][:12]

    out = w.activate(key, create_fn)
    if out.get("status") != "created":
        return {"id": key, "status": "held_for_approval", "note": "run approve first; nothing created"}
    return {"id": key, "status": "created", "watch_id": out.get("watch_id")}


async def watch_test(watch_id: str) -> dict:
    """Fire the free /test alert: re-attest the watched company as of today, snapshot it, mark the stored
    case file lines STALE. The same signal date again is a no-op."""
    import json as _json
    w = _watchers()
    found = _watch_by_id(watch_id) if w is not None else None
    if found is None or not found[1].get("watch_id"):
        raise RequestError(f"no active watcher {watch_id!r}; approve and issue the watch first")
    key, ent = found
    wid, cid, field, dom = ent["watch_id"], int(ent["company_id"]), ent.get("field") or "headcount", ent["domain"]
    try:
        w.test(wid)  # free
    except Exception:
        pass
    s = get_session()
    d = today()
    line, _, _ = await attest_full(dom, field, d)
    h = _sha(line.model_dump_json())
    stale = []
    for aid in store.all_ids():
        try:
            obj = store.load(aid)
        except RequestError:
            continue
        if isinstance(obj, CaseFile) and obj.attestation and obj.attestation.entity.crustdata_company_id == cid:
            if any(l.field == field for l in obj.attestation.lines):
                stale.append(f"{obj.id}#{field}")
    snap, is_new = w.on_alert(wid, cid, field, d, h, stale)
    if not is_new:
        return {"status": "no_op", "reason": "duplicate signal date (or monthly alert cap)",
                "snapshot": _jsonable(snap), "current_line": _jsonable(line)}
    for sid in stale:
        cid_ = sid.split("#")[0]
        m = store.meta_load(cid_)
        lst = list(m.get("stale") or [])
        lst.append({"line": sid, "field": field, "snapshot": _json.loads(snap.model_dump_json()),
                    "newer_point": line.point_date.isoformat() if line.point_date else None})
        store.meta_update(cid_, stale=lst)
    return {"status": "alert", "snapshot": _jsonable(snap), "stale_line_ids": stale,
            "current_line": _jsonable(line), "alert_cost_credits": 5.0}


async def show(artifact_id: str) -> dict:
    obj = store.load(artifact_id)
    m = store.meta_load(artifact_id)
    d = obj.model_dump(mode="json")
    stale = {x["field"] for x in m.get("stale") or []}
    if isinstance(obj, CaseFile) and d.get("attestation"):
        for ln in d["attestation"]["lines"]:
            if ln["field"] in stale:
                ln["stale"] = True
                ln["stale_note"] = "STALE: a watcher alert reports newer data; re-attest before relying on this line"
    return {"artifact": d, "approval": m.get("approval"), "stale": m.get("stale") or []}


def cost_note(c) -> str:
    mode = "replay" if (c.calls == 0 and c.cache_hits > 0) else "live"
    return (f"\u20b9{c.inr:.2f} spent this run ({mode}); \u20b9{c.recorded_inr:.2f} measured cost of the stored "
            f"copies ({c.recorded_credits:g} credits)")


async def cost() -> dict:
    """Ledger view across processes: persisted run ledgers plus every stored case file's cost."""
    from backend.crust.ledger import CREDIT_TO_INR
    files = []
    for aid in store.all_ids():
        try:
            obj = store.load(aid)
        except RequestError:
            continue
        if isinstance(obj, CaseFile):
            c = obj.cost
            files.append({"id": obj.id, "kind": obj.kind, "domain": obj.request.get("domain"),
                          "credits": c.credits, "inr": c.inr, "recorded_credits": c.recorded_credits,
                          "recorded_inr": c.recorded_inr, "label": cost_note(c)})
    from .session import state_dir
    spent = 0.0
    ld = state_dir() / "ledger"
    for p in (ld.glob("*.jsonl") if ld.exists() else []):
        from backend.crust.ledger import Ledger
        spent += Ledger(p.stem, ld).total
    return {"case_files": files, "ledger_credits_spent": round(spent, 6),
            "ledger_inr_spent": round(spent * CREDIT_TO_INR, 2),
            "total_recorded_credits": round(sum(f["recorded_credits"] for f in files), 6)}
