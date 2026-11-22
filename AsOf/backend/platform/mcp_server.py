"""FastMCP stdio server for AsOf. Run: python -m backend.platform.mcp_server

Tools delegate to `backend.pipeline.api` (imported lazily; injectable registry for tests).
Every result is {"result": ..., "cost": CostSummary-dict}.
"""
from __future__ import annotations

import importlib
import inspect
import json
from typing import Any, Callable

try:  # mcp 1.x
    from mcp.server.fastmcp import FastMCP
except ImportError:  # mcp 2.x renamed FastMCP -> MCPServer
    from mcp.server.mcpserver import MCPServer as FastMCP


TOOL_NAMES = ["resolve", "attest", "clear_counterparty", "dispute_file", "observe",
              "audit_claims", "request_evidence", "watch", "issue", "cost"]

# Expected backend.pipeline.api signatures (each returns a pydantic model/dict; cost optional):
#   resolve(name: str|None=None, domain: str|None=None) -> ResolveResult
#   attest(field: str, as_of: str, domain: str|None=None, company_id: int|None=None) -> AttestLine
#   clear_counterparty(domain: str) -> CaseFile
#   dispute_file(domain: str, as_of: str) -> CaseFile
#   observe(domain: str, field: str, d1: str, d2: str) -> dict|list[AttestLine]
#   audit_claims(domain: str, claims: list[dict]) -> AuditReport
#   request_evidence(target: str, items: list[str]) -> EvidenceRequest
#   watch(domain: str) -> dict
#   issue(artifact_id: str) -> dict          (sends only what a human approved, else held_for_approval)
#   cost() -> dict   (cross-process ledger view)
# Each may take an optional run_id kwarg; the server passes run_id=<tool>-<uuid> when accepted.


def _default_registry() -> dict[str, Callable]:
    try:
        api = importlib.import_module("backend.pipeline.api")
    except ImportError as e:
        err = f"backend.pipeline.api is not available: {e}"

        def missing(**_kw):
            raise RuntimeError(err)
        return {n: missing for n in TOOL_NAMES}
    def lazy(n):
        def f(**kw):
            fn = getattr(api, n, None)
            if fn is None:
                raise RuntimeError(f"backend.pipeline.api.{n} is missing")
            return fn(**kw)
        return f
    return {n: lazy(n) for n in TOOL_NAMES}


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

    async def call(tool: str, /, **kw) -> dict:
        try:
            out = reg[tool](**{k: v for k, v in kw.items() if v is not None})
            if inspect.isawaitable(out):
                out = await out
        except Exception as e:  # clear error, never a crash or a guess
            return {"error": f"{type(e).__name__}: {e}",
                    "cost": {"credits": 0.0, "inr": 0.0, "calls": 0, "cache_hits": 0}}
        return {"result": _plain(out), "cost": _cost_of(out)}

    @mcp.tool()
    async def resolve(name: str | None = None, domain: str | None = None) -> dict:
        """Resolve a company by domain or name. Several candidates and no domain -> CANNOT_RESOLVE."""
        return await call("resolve", name=name, domain=domain)

    @mcp.tool()
    async def attest(field: str, as_of: str, domain: str | None = None, company_id: int | None = None) -> dict:
        """Attest one field as of a date (YYYY-MM-DD) with a dated source, or refuse with a code."""
        return await call("attest", field=field, as_of=as_of, domain=domain, company_id=company_id)

    @mcp.tool()
    async def clear_counterparty(domain: str) -> dict:
        """Clearance case file as of today, all record types. Issuing it is held for approval."""
        return await call("clear_counterparty", domain=domain)

    @mcp.tool()
    async def dispute_file(domain: str, as_of: str) -> dict:
        """Dispute case file as of a past date (YYYY-MM-DD). Issuing it is held for approval."""
        return await call("dispute_file", domain=domain, as_of=as_of)

    @mcp.tool()
    async def observe(domain: str, field: str, d1: str, d2: str) -> dict:
        """Two attested lines side by side. Never a growth or ratio verdict."""
        return await call("observe", domain=domain, field=field, d1=d1, d2=d2)

    @mcp.tool()
    async def audit_claims(domain: str, claims: list[dict]) -> dict:
        """Audit structured claims [{id,text,field,value,as_of}] against dated records."""
        return await call("audit_claims", domain=domain, claims=claims)

    @mcp.tool()
    async def request_evidence(target: str, items: list[str]) -> dict:
        """Draft a held evidence request (Not a negative finding). Sending needs approval."""
        return await call("request_evidence", target=target, items=items)

    @mcp.tool()
    async def watch(domain: str) -> dict:
        """Create a watcher (held for approval; alerts cost 5 credits each)."""
        return await call("watch", domain=domain)

    @mcp.tool()
    async def issue(id: str) -> dict:
        """Send a case file / report / request ONLY if a human already approved it (via the CLI);
        otherwise returns held_for_approval. There is no approve tool: approval is human-only."""
        return await call("issue", artifact_id=id)

    @mcp.tool()
    async def cost() -> dict:
        """Ledger view: credits and INR spent, plus the recorded cost of each stored case file."""
        return await call("cost")

    return mcp


def main() -> None:
    build_server().run(transport="stdio")


if __name__ == "__main__":
    main()
