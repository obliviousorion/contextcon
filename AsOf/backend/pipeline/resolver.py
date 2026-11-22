"""Resolution: autocomplete (free) -> identify. Domain wins; a bare name with >1 candidate cannot resolve."""
from __future__ import annotations

import re
from typing import Any

from backend.models import Candidate, Entity, ResolveResult

from .errors import RequestError
from .session import Session

_DOMAIN = re.compile(r"^(?=.{4,253}$)([a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,24}$")


def normalize_domain(raw: Any) -> str:
    if not isinstance(raw, str) or not raw.strip():
        raise RequestError("a domain is required, e.g. delhivery.com")
    d = raw.strip().lower()
    d = re.sub(r"^[a-z]+://", "", d)
    d = d.split("/")[0].split("?")[0]
    if d.startswith("www."):
        d = d[4:]
    if not _DOMAIN.match(d):
        raise RequestError(f"not a valid domain: {raw[:60]!r}")
    return d


def _candidates(items: list) -> list[Candidate]:
    out = []
    for it in items:
        for m in (it or {}).get("matches") or []:
            cd = m.get("company_data") or {}
            bi = cd.get("basic_info") or {}
            if cd.get("crustdata_company_id") is None:
                continue
            out.append(Candidate(crustdata_company_id=int(cd["crustdata_company_id"]), name=bi.get("name"),
                                 domains=list(bi.get("all_domains") or []), confidence=m.get("confidence_score")))
    return out


def _cannot(missing: str, cands: list[Candidate] | None = None) -> ResolveResult:
    return ResolveResult(status="cannot_resolve", candidates=cands or [], missing=missing)


def _register(s: Session, c_data: dict, resolved_by: str, ev: dict, key: str | None = None) -> Entity:
    """One Entity per crustdata_company_id. Only the domain identify was asked about (`key`) is cached:
    an alias from all_domains is not proof the alias belongs to this company alone (live identify on
    drl.aero matched Delhivery and Delhivery Robotics), so an alias costs one identify, never a guess."""
    bi = c_data.get("basic_info") or {}
    cid = int(c_data["crustdata_company_id"])
    ent = s.entity_by_id.get(cid)
    if ent is None:
        domains = [d.lower() for d in (bi.get("all_domains") or [])]
        if bi.get("primary_domain") and bi["primary_domain"].lower() not in domains:
            domains.append(bi["primary_domain"].lower())
        ent = Entity(crustdata_company_id=cid, name=bi.get("name"), domains=domains, resolved_by=resolved_by,
                     evidence_id="E1")
        s.entity_by_id[cid] = ent
        s.entity_evidence[cid] = ev
    if key:
        s.entities[key] = ent
    return ent


async def resolve(s: Session, name: str | None = None, domain: str | None = None) -> ResolveResult:
    if domain is not None and str(domain).strip():
        return await _by_domain(s, normalize_domain(domain))
    if name is not None and str(name).strip():
        return await _by_name(s, str(name).strip()[:200])
    raise RequestError("give a company name or a domain")


async def _by_domain(s: Session, d: str) -> ResolveResult:
    if d in s.entities:
        return ResolveResult(status="resolved", entity=s.entities[d])
    res = await s.identify_domain(d)
    if not res.ok:
        return _cannot(f"a reachable source ({res.kind}: {res.reason})")
    items = res.data if isinstance(res.data, list) else []
    cands = _candidates(items)
    if not cands:
        return _cannot(f"a domain Crustdata recognises: {d} was not found; "
                       "registration documents (GSTIN/CIN) would settle it")
    ids = {c.crustdata_company_id for c in cands}
    if len(ids) > 1:
        return _cannot("a domain that matches exactly one company", cands)
    cd = next(m["company_data"] for it in items for m in it.get("matches") or [])
    owned = {x.lower() for x in (cd.get("basic_info") or {}).get("all_domains") or []}
    owned.add(str((cd.get("basic_info") or {}).get("primary_domain") or "").lower())
    if d not in owned:
        return _cannot(f"a domain listed on the matched record: {d} is not among its domains", cands)
    bi = cd.get("basic_info") or {}
    ev = {"source_endpoint": "/company/identify", "field_path": "basic_info.all_domains",
          "excerpt": f"domains {sorted(owned - {''})} -> crustdata_company_id {cd['crustdata_company_id']}"[:400],
          "retrieved_at": res.retrieved_at, "cache_key": res.cache_key, "matched_on": d, "name": bi.get("name")}
    return ResolveResult(status="resolved", entity=_register(s, cd, "domain", ev, key=d))


async def _by_name(s: Session, name: str) -> ResolveResult:
    await s.client.autocomplete({"field": "basic_info.name", "query": name, "limit": 5})  # free; failure is fine
    res = await s.client.company_identify({"names": [name]})
    if res.ok and res.cache_hit:
        s.served["identify"] += 1
    if not res.ok:
        return _cannot(f"a reachable source ({res.kind}: {res.reason}); or a domain")
    items = res.data if isinstance(res.data, list) else []
    cands = _candidates(items)
    if not cands:
        return _cannot("a domain (no company matched that name)")
    if len(cands) > int(s.cfg.get("resolve", {}).get("require_domain_when_candidates_gt", 1)):
        return _cannot("a domain", cands)
    cd = next(m["company_data"] for it in items for m in it.get("matches") or [])
    ev = {"source_endpoint": "/company/identify", "field_path": "basic_info.name",
          "excerpt": f"name {name!r} -> crustdata_company_id {cd['crustdata_company_id']}"[:400],
          "retrieved_at": res.retrieved_at, "cache_key": res.cache_key}
    return ResolveResult(status="resolved", entity=_register(s, cd, "id", ev))
