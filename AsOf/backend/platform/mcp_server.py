"""FastMCP stdio server for AsOf. Run: python -m backend.platform.mcp_server

Tools delegate to `backend.pipeline.api` (imported lazily; injectable registry for tests).
Every result is {"result": ..., "cost": CostSummary-dict}.
"""
from __future__ import annotations

import importlib
import json
from typing import Any, Callable

try:  # mcp 1.x
    from mcp.server.fastmcp import FastMCP
except ImportError:  # mcp 2.x renamed FastMCP -> MCPServer
    from mcp.server.mcpserver import MCPServer as FastMCP

from . import actions

TOOL_NAMES = ["resolve", "attest", "clear_counterparty", "dispute_file", "observe",
              "audit_claims", "request_evidence", "watch", "approve"]

# Expected backend.pipeline.api signatures (each returns a pydantic model/dict; cost optional):
#   resolve(name: str|None=None, domain: str|None=None) -> ResolveResult
#   attest(field: str, as_of: str, domain: str|None=None, company_id: int|None=None) -> AttestLine
#   clear_counterparty(domain: str) -> CaseFile
#   dispute_file(domain: str, as_of: str) -> CaseFile
#   observe(domain: str, field: str, d1: str, d2: str) -> dict|list[AttestLine]
#   audit_claims(domain: str, claims: list[dict]) -> AuditReport
#   request_evidence(target: str, items: list[str]) -> EvidenceRequest
#   watch(domain: str) -> dict
# Each may take an optional run_id kwarg; the server passes run_id=<tool>-<uuid> when accepted.


def _default_registry() -> dict[str, Callable]:
    try:
        api = importlib.import_module("backend.pipeline.api")
    except ImportError as e:
        err = f"backend.pipeline.api is not available: {e}"

        def missing(**_kw):
            raise RuntimeError(err)
        return {n: missing for n in TOOL_NAMES if n != "approve"}
    def lazy(n):
        def f(**kw):
            fn = getattr(api, n, None)
            if fn is None:
                raise RuntimeError(f"backend.pipeline.api.{n} is missing")
            return fn(**kw)
        return f
    return {n: lazy(n) for n in TOOL_NAMES if n != "approve"}


def _plain(x: Any) -> Any:
    if hasattr(x, "model_dump_json"):
        return json.loads(x.model_dump_json())
    if isinstance(x, (list, tuple)):
        return [_plain(i) for i in x]
    if isinstance(x, dict):
        return {k: _plain(v) for k, v in x.items()}
    return x


def _cost_of(out: Any) -> dict:
    plain = _plain(out)
    if isinstance(plain, dict):
        if isinstance(plain.get("cost"), dict):
            return plain["cost"]
        if isinstance(plain.get("cost_summary"), dict):
            return plain["cost_summary"]
    return {"credits": 0.0, "inr": 0.0, "calls": 0, "cache_hits": 0}


def build_server(registry: dict[str, Callable] | None = None) -> FastMCP:
    reg = registry if registry is not None else _default_registry()
    mcp = FastMCP("asof")

    def call(tool: str, /, **kw) -> dict:
        try:
            out = reg[tool](**{k: v for k, v in kw.items() if v is not None})
        except Exception as e:  # clear error, never a crash or a guess
            return {"error": f"{type(e).__name__}: {e}",
                    "cost": {"credits": 0.0, "inr": 0.0, "calls": 0, "cache_hits": 0}}
        return {"result": _plain(out), "cost": _cost_of(out)}

    @mcp.tool()
    def resolve(name: str | None = None, domain: str | None = None) -> dict:
        """Resolve a company by domain or name. Several candidates and no domain -> CANNOT_RESOLVE."""
        return call("resolve", name=name, domain=domain)

    @mcp.tool()
    def attest(field: str, as_of: str, domain: str | None = None, company_id: int | None = None) -> dict:
        """Attest one field as of a date (YYYY-MM-DD) with a dated source, or refuse with a code."""
        return call("attest", field=field, as_of=as_of, domain=domain, company_id=company_id)

    @mcp.tool()
    def clear_counterparty(domain: str) -> dict:
        """Clearance case file as of today, all record types. Issuing it is held for approval."""
        return call("clear_counterparty", domain=domain)

    @mcp.tool()
    def dispute_file(domain: str, as_of: str) -> dict:
        """Dispute case file as of a past date (YYYY-MM-DD). Issuing it is held for approval."""
        return call("dispute_file", domain=domain, as_of=as_of)

    @mcp.tool()
    def observe(domain: str, field: str, d1: str, d2: str) -> dict:
        """Two attested lines side by side. Never a growth or ratio verdict."""
        return call("observe", domain=domain, field=field, d1=d1, d2=d2)

    @mcp.tool()
    def audit_claims(domain: str, claims: list[dict]) -> dict:
        """Audit structured claims [{id,text,field,value,as_of}] against dated records."""
        return call("audit_claims", domain=domain, claims=claims)

    @mcp.tool()
    def request_evidence(target: str, items: list[str]) -> dict:
        """Draft a held evidence request (Not a negative finding). Sending needs approval."""
        return call("request_evidence", target=target, items=items)

    @mcp.tool()
    def watch(domain: str) -> dict:
        """Create a watcher (held for approval; alerts cost 5 credits each)."""
        return call("watch", domain=domain)

    @mcp.tool()
    def approve(key: str) -> dict:
        """Approve a held action by idempotency key. A double approval is a no-op."""
        first = actions.approve(key)
        return {"result": {"key": key, "approved": True, "first_approval": first},
                "cost": {"credits": 0.0, "inr": 0.0, "calls": 0, "cache_hits": 0}}

    return mcp


def main() -> None:
    build_server().run(transport="stdio")


if __name__ == "__main__":
    main()
