"""Typed results returned by the Crustdata client. The client never raises on bad responses."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class CrustResult:
    ok: bool
    kind: str = "ok"  # ok|unavailable|endpoint_disabled|payment_required|held|replay_miss
    status: int | None = None
    data: Any = None
    reason: str | None = None
    retrieved_at: str | None = None  # ISO ts of the source record (required for citations)
    cache_hit: bool = False
    credits: float = 0.0
    cache_key: str | None = None
    endpoint: str = ""
    extra: dict[str, Any] = field(default_factory=dict)

    def __bool__(self) -> bool:
        return self.ok


class EndpointDisabled(CrustResult):
    pass


def unavailable(endpoint: str, reason: str, status: int | None = None, kind: str = "unavailable",
                key: str | None = None) -> CrustResult:
    return CrustResult(ok=False, kind=kind, status=status, reason=reason, endpoint=endpoint, cache_key=key)


def first_list(data: Any, *keys: str) -> list:
    """Defensively find a result list in a response."""
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        for k in keys or ("results", "companies", "profiles", "people", "jobs", "data"):
            v = data.get(k)
            if isinstance(v, list):
                return v
    return []


def parse_company_enrich(data: Any) -> list[dict]:
    """Return company_data dicts from a /company/enrich response (list of {matches:[{company_data}]})."""
    out: list[dict] = []
    for item in first_list(data):
        if not isinstance(item, dict):
            continue
        for m in item.get("matches") or []:
            cd = (m or {}).get("company_data") if isinstance(m, dict) else None
            if isinstance(cd, dict):
                out.append(cd)
    return out
