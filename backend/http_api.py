"""Local HTTP wrapper over backend.pipeline.api, for the web UI.

Run:  uv run python -m backend.http_api            (MODE defaults to replay; binds 127.0.0.1:8787)
UI:   cd frontend && VITE_API_URL=http://127.0.0.1:8787 npm run dev

Endpoints (JSON):
  GET  /api/casefile?tool=clear|dispute|attest|resolve&domain=...&as_of=YYYY-MM-DD
  POST /api/issue    {"id": "CF-..."}   sends only what a person approved, else held_for_approval
  POST /api/approve  {"id": "CF-..."}   needs header X-AsOf-Approval-Token (printed at startup)
  GET  /api/cost                       ledger view: every stored case file with spent + measured cost
  GET  /api/health                     mode and today's date
  GET  /api/files/{id}                 one stored case file, its approval record and STALE marks
  GET  /api/attest?domain=&field=&as_of=           one line, plus subsequent events
  GET  /api/observe?domain=&field=&d1=&d2=         two dated lines side by side (never a growth verdict)
  POST /api/audit    {"domain": ..., "claims": [{id, text, field, value, as_of}]}
  POST /api/evidence_request {"target": ..., "items": [...]}
  POST /api/watch    {"domain": ...}   held for approval; approve + issue its key to create it
  POST /api/watch_test {"id": "watch:..."}  free test alert: re-attests today, marks lines STALE

Approval stays a person's act. Any local process can reach an HTTP port, so approve needs the
one-time token this server prints to its own terminal. Nothing that only calls the API can approve.
"""
from __future__ import annotations

import hmac
import os
import re
import secrets
from typing import Any

from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.middleware.cors import CORSMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route

os.environ.setdefault("MODE", "replay")

from backend.pipeline import api  # noqa: E402  (after MODE is set)
from backend.pipeline.errors import RequestError  # noqa: E402

UI_ORIGINS = ["http://127.0.0.1:5173", "http://localhost:5173"]
_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def _plain(x: Any) -> Any:
    if hasattr(x, "model_dump"):
        return x.model_dump(mode="json")
    if isinstance(x, (list, tuple)):
        return [_plain(i) for i in x]
    if isinstance(x, dict):
        return {k: _plain(v) for k, v in x.items()}
    return x


def _err(msg: str, status: int = 400) -> JSONResponse:
    return JSONResponse({"error": msg}, status_code=status)


def _looks_like_domain(s: str) -> bool:
    return "." in s and " " not in s.strip()


async def casefile(request: Request) -> JSONResponse:
    q = request.query_params
    tool = (q.get("tool") or "clear").strip()
    target = (q.get("domain") or "").strip()
    as_of = (q.get("as_of") or "").strip()
    if not target:
        return _err("domain is required (or a company name, for resolve)")
    if as_of and not _DATE.match(as_of):
        return _err("as_of must be YYYY-MM-DD")
    try:
        if tool == "resolve":
            kw = {"domain": target} if _looks_like_domain(target) else {"name": target}
            return JSONResponse({"resolve": _plain(await api.resolve(**kw))})
        if not _looks_like_domain(target):
            # A bare name cannot be attested; show why instead of guessing a company.
            return JSONResponse({"resolve": _plain(await api.resolve(name=target))})
        if tool == "clear":
            cf = await api.clear_counterparty(target)
        elif tool in ("dispute", "attest"):
            if not as_of:
                return _err("as_of is required for a dispute file")
            # The UI shows a whole file; attest in the UI is the dispute file as of D (every field).
            cf = await api.dispute_file(target, as_of)
        else:
            return _err(f"unknown tool {tool!r}; use clear, dispute, attest or resolve")
    except RequestError as e:
        return _err(str(e))
    return JSONResponse({"caseFile": _plain(cf)})


async def _body_id(request: Request) -> str | None:
    try:
        body = await request.json()
    except Exception:
        return None
    v = body.get("id") if isinstance(body, dict) else None
    return v.strip() if isinstance(v, str) and v.strip() else None


async def issue(request: Request) -> JSONResponse:
    artifact_id = await _body_id(request)
    if not artifact_id:
        return _err('body must be {"id": "<case file id>"}')
    try:
        return JSONResponse(_plain(await api.issue(artifact_id)))
    except RequestError as e:
        return _err(str(e))


async def approve(request: Request) -> JSONResponse:
    expected = request.app.state.approval_token
    given = request.headers.get("x-asof-approval-token", "")
    if not expected or not hmac.compare_digest(given.encode(), expected.encode()):
        return _err("approval needs the token printed in the API server's terminal "
                    "(or run: uv run python -m backend.cli approve <id>)", 403)
    artifact_id = await _body_id(request)
    if not artifact_id:
        return _err('body must be {"id": "<case file id>"}')
    try:
        return JSONResponse(_plain(await api.approve(artifact_id, by="ui")))
    except RequestError as e:
        return _err(str(e), 409)


async def cost(request: Request) -> JSONResponse:
    return JSONResponse(_plain(await api.cost()))


def _date_param(q, name: str, required: bool = True) -> str | None:
    v = (q.get(name) or "").strip()
    if not v:
        if required:
            raise RequestError(f"{name} is required (YYYY-MM-DD)")
        return None
    if not _DATE.match(v):
        raise RequestError(f"{name} must be YYYY-MM-DD")
    return v


async def _json_body(request: Request) -> dict:
    try:
        body = await request.json()
    except Exception:
        raise RequestError("body must be JSON")
    if not isinstance(body, dict):
        raise RequestError("body must be a JSON object")
    return body


def _guard(fn):
    async def run(request: Request) -> JSONResponse:
        try:
            return await fn(request)
        except RequestError as e:
            return _err(str(e))
        except FileNotFoundError:
            return _err("no stored artifact with that id", 404)
    return run


@_guard
async def health(request: Request) -> JSONResponse:
    from backend.pipeline.session import today
    return JSONResponse({"ok": True, "mode": os.environ.get("MODE", "replay"), "today": today().isoformat()})


@_guard
async def file_detail(request: Request) -> JSONResponse:
    return JSONResponse(_plain(await api.show(request.path_params["id"])))


@_guard
async def attest_one(request: Request) -> JSONResponse:
    q = request.query_params
    domain, field = (q.get("domain") or "").strip(), (q.get("field") or "").strip()
    if not domain or not field:
        raise RequestError("domain and field are required")
    line, subsequent, evidence = await api.attest_full(domain, field, _date_param(q, "as_of"))
    return JSONResponse({"line": _plain(line), "subsequent_events": _plain(subsequent), "evidence": _plain(evidence)})


@_guard
async def observe(request: Request) -> JSONResponse:
    q = request.query_params
    domain, field = (q.get("domain") or "").strip(), (q.get("field") or "").strip()
    if not domain or not field:
        raise RequestError("domain and field are required")
    a, b = await api.observe(domain, field, _date_param(q, "d1"), _date_param(q, "d2"))
    return JSONResponse({"lines": _plain([a, b])})


@_guard
async def audit(request: Request) -> JSONResponse:
    body = await _json_body(request)
    return JSONResponse({"report": _plain(await api.audit_claims(str(body.get("domain") or ""), body.get("claims")))})


@_guard
async def evidence_request(request: Request) -> JSONResponse:
    body = await _json_body(request)
    return JSONResponse({"request": _plain(await api.request_evidence(str(body.get("target") or ""), body.get("items") or []))})


@_guard
async def watch(request: Request) -> JSONResponse:
    body = await _json_body(request)
    return JSONResponse(_plain(await api.watch(str(body.get("domain") or ""))))


@_guard
async def watch_test(request: Request) -> JSONResponse:
    body = await _json_body(request)
    return JSONResponse(_plain(await api.watch_test(str(body.get("id") or ""))))


def build_app(approval_token: str | None = None) -> Starlette:
    app = Starlette(
        routes=[
            Route("/api/casefile", casefile, methods=["GET"]),
            Route("/api/issue", issue, methods=["POST"]),
            Route("/api/approve", approve, methods=["POST"]),
            Route("/api/cost", cost, methods=["GET"]),
            Route("/api/health", health, methods=["GET"]),
            Route("/api/files/{id}", file_detail, methods=["GET"]),
            Route("/api/attest", attest_one, methods=["GET"]),
            Route("/api/observe", observe, methods=["GET"]),
            Route("/api/audit", audit, methods=["POST"]),
            Route("/api/evidence_request", evidence_request, methods=["POST"]),
            Route("/api/watch", watch, methods=["POST"]),
            Route("/api/watch_test", watch_test, methods=["POST"]),
        ],
        middleware=[Middleware(CORSMiddleware, allow_origins=UI_ORIGINS, allow_methods=["GET", "POST"],
                               allow_headers=["content-type", "x-asof-approval-token"])],
    )
    app.state.approval_token = approval_token
    return app


def main() -> None:
    import uvicorn

    port = int(os.environ.get("ASOF_HTTP_PORT", "8787"))
    token = secrets.token_urlsafe(9)
    print(f"AsOf HTTP API on http://127.0.0.1:{port}  (MODE={os.environ['MODE']})", flush=True)
    print(f"Approval token for this session (paste it in the UI when you approve): {token}", flush=True)
    uvicorn.run(build_app(token), host="127.0.0.1", port=port, log_level="warning")


if __name__ == "__main__":
    main()
