"""python -m backend.cli <tool> [args]  -> JSON on stdout. Errors are JSON too, never a stack trace."""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
from typing import Any


def _j(v: Any) -> Any:
    if hasattr(v, "model_dump"):
        return v.model_dump(mode="json")
    if isinstance(v, (list, tuple)):
        return [_j(x) for x in v]
    if isinstance(v, dict):
        return {k: _j(x) for k, x in v.items()}
    return v


CLAIM_HELP = """claim schema (JSON list): {id: str, text: str, field: str, value: any|null, as_of: YYYY-MM-DD|null}
  field is one of: existence, listing, headcount, revenue_band, domains (anything else is cannot_verify)
example:
  audit tciexpress.in --claims '[{"id":"k1","text":"TCI had 418 staff at end of 2019","field":"headcount","value":418,"as_of":"2019-12-30"}]'
"""


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="asof", description="AsOf: what is provably true about a company, and as of when.")
    sub = p.add_subparsers(dest="tool", required=True)
    r = sub.add_parser("resolve"); r.add_argument("domain", nargs="?"); r.add_argument("--name"); r.add_argument("--domain", dest="domain_opt")
    a = sub.add_parser("attest"); a.add_argument("domain"); a.add_argument("field"); a.add_argument("as_of")
    c = sub.add_parser("clear"); c.add_argument("domain")
    sub.add_parser("clear_counterparty").add_argument("domain")
    d = sub.add_parser("dispute"); d.add_argument("domain"); d.add_argument("as_of")
    d2 = sub.add_parser("dispute_file"); d2.add_argument("domain"); d2.add_argument("as_of")
    o = sub.add_parser("observe"); [o.add_argument(x) for x in ("domain", "field", "d1", "d2")]
    u = sub.add_parser("audit", formatter_class=argparse.RawDescriptionHelpFormatter,
                       description="Grade structured claims against dated records. No LLM splitting.",
                       epilog=CLAIM_HELP)
    u.add_argument("domain"); u.add_argument("--claims", help="JSON list of claims, or @file")
    e = sub.add_parser("request_evidence"); e.add_argument("target"); e.add_argument("items", nargs="*")
    ap = sub.add_parser("approve", help="human approval of a draft (case file, report, evidence request, watch id)")
    ap.add_argument("id"); ap.add_argument("--by", help="approver name (default: $USER)")
    sub.add_parser("issue").add_argument("id")
    sub.add_parser("show").add_argument("id")
    sub.add_parser("watch_test").add_argument("watch_id")
    sub.add_parser("watch").add_argument("domain")
    sub.add_parser("cost")
    return p


def _with_note(cf) -> dict:
    from backend.pipeline.api import cost_note
    d = _j(cf)
    d["cost_note"] = cost_note(cf.cost)
    return d


async def run(argv: list[str]) -> Any:
    from backend.pipeline import api
    from backend.pipeline.errors import RequestError
    from backend.pipeline.session import get_session

    ns = build_parser().parse_args(argv)
    t = ns.tool
    if t == "resolve":
        pos = ns.domain
        if pos and not ns.name and not ns.domain_opt and (" " in pos.strip() or "." not in pos):
            return await api.resolve(name=pos)  # looks like a company name, not a domain
        return await api.resolve(name=ns.name, domain=ns.domain_opt or pos)
    if t == "attest":
        line, subs, ev = await api.attest_full(ns.domain, ns.field, ns.as_of)
        return {"line": line, "subsequent_events": subs, "evidence": ev, "cost": get_session().cost_since(0)}
    if t in ("clear", "clear_counterparty"):
        return _with_note(await api.clear_counterparty(ns.domain))
    if t in ("dispute", "dispute_file"):
        return _with_note(await api.dispute_file(ns.domain, ns.as_of))
    if t == "observe":
        a, b = await api.observe(ns.domain, ns.field, ns.d1, ns.d2)
        return {"d1": a, "d2": b, "note": "Two dated values side by side. No growth or ratio verdict."}
    if t == "audit":
        raw = ns.claims or ""
        if raw.startswith("@"):
            try:
                raw = open(raw[1:]).read()
            except OSError:
                raise RequestError("cannot read the claims file") from None
        try:
            claims = json.loads(raw) if raw.strip() else []
        except ValueError:
            raise RequestError("--claims must be a JSON list of structured claims") from None
        return await api.audit_claims(ns.domain, claims)
    if t == "request_evidence":
        return await api.request_evidence(ns.target, ns.items)
    if t == "approve":
        return await api.approve(ns.id, by=ns.by)
    if t == "issue":
        return await api.issue(ns.id)
    if t == "watch":
        return await api.watch(ns.domain)
    if t == "show":
        return await api.show(ns.id)
    if t == "watch_test":
        return await api.watch_test(ns.watch_id)
    if t == "cost":
        return await api.cost()
    raise RequestError(f"unknown tool {t!r}")


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    try:
        out = asyncio.run(run(argv))
    except SystemExit as e:  # argparse usage error
        if e.code in (0, None):
            return 0
        print(json.dumps({"error": "bad usage: run with -h for the tool list"}))
        return 2
    except Exception as e:
        from backend.pipeline.errors import RequestError
        if isinstance(e, RequestError):
            print(json.dumps({"error": str(e)}))
            return 2
        print(json.dumps({"error": f"unexpected {type(e).__name__}; request not completed"}))
        return 1
    print(json.dumps(_j(out), indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
