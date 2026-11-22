"""Headless CLI. Every request runs without the UI.

  bd run requests/T2_peer_share.json [--chaos] [--mode replay|record|live] [--run-id X] [--fresh]
  bd approve <intent_key> [--by NAME]      a person approves one action (double approve = one action)
  bd act <run_id> [--chaos]                send approved actions of a run, exactly once
  bd status [run_id]                        runs, actions, ledger
  bd ledger [run_id]
  bd forget <profile_url>                   consent withdrawn: delete the persona's facts
  bd sandbox                                start the sandbox receiver (port 8765)
  bd serve                                  HTTP API + UI (port 8787)
  bd smoke                                  live smoke test: reproduce the job-post counts (count-only, 0 credits)
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

from . import actions
from .store import Store, h


def _load(path: str) -> dict:
    return json.loads(Path(path).read_text())


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="bd")
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run"); r.add_argument("request"); r.add_argument("--chaos", action="store_true")
    r.add_argument("--mode"); r.add_argument("--run-id"); r.add_argument("--fresh", action="store_true")
    r.add_argument("--json", action="store_true")
    a = sub.add_parser("approve"); a.add_argument("key"); a.add_argument("--by", default="person")
    act = sub.add_parser("act"); act.add_argument("run_id"); act.add_argument("--chaos", action="store_true")
    s = sub.add_parser("status"); s.add_argument("run_id", nargs="?")
    l = sub.add_parser("ledger"); l.add_argument("run_id", nargs="?")
    f = sub.add_parser("forget"); f.add_argument("profile_url")
    sub.add_parser("sandbox"); sv = sub.add_parser("serve"); sv.add_argument("--port", type=int, default=8787)
    sm = sub.add_parser("smoke"); sm.add_argument("--mode", default="live")
    wc = sub.add_parser("watch-create"); wc.add_argument("profile_url"); wc.add_argument("--mode", default="live")
    wr = sub.add_parser("watch-register"); wr.add_argument("watch_id"); wr.add_argument("profile_url")
    wp = sub.add_parser("watch-pull"); wp.add_argument("watch_id"); wp.add_argument("--mode", default="live")
    wp.add_argument("--since", default="2026-09-01"); wp.add_argument("--as-of", default="2026-11-22")
    args = ap.parse_args(argv)
    store = Store()

    if args.cmd == "run":
        from .pipeline import Run
        from .report import markdown
        req = _load(args.request)
        run_id = args.run_id or (f"{req.get('id','run')}-{h(req, time.time())[:6]}" if args.fresh else None)
        case = Run(store, req, run_id=run_id, chaos=args.chaos, mode=args.mode).go()
        out = Path("state") / "cases"; out.mkdir(parents=True, exist_ok=True)
        (out / f"{case['run_id']}.json").write_text(json.dumps(case, indent=1, default=str))
        (out / f"{case['run_id']}.md").write_text(markdown(case))
        print(json.dumps(case, indent=1, default=str) if args.json else markdown(case))
        return 0 if case["status"] in ("finished", "refused") else 2
    if args.cmd == "approve":
        res = actions.approve(store, args.key, args.by)
        print(json.dumps(res)); return 0 if res["approved"] or res["already"] else 1
    if args.cmd == "act":
        from .pipeline import Run
        row = store.q("SELECT request FROM runs WHERE run_id=?", args.run_id)
        if not row:
            print("no such run"); return 1
        run = Run(store, json.loads(row[0]["request"]), run_id=args.run_id, chaos=args.chaos)
        case: dict = {"status": "finished"}
        run._act(case)
        print(json.dumps([{"key": i["key"], "status": i["status"]} for i in actions.list_all(store, args.run_id)]))
        return 0 if case["status"] == "finished" else 2
    if args.cmd == "status":
        for row in store.q("SELECT run_id, status, started, finished FROM runs ORDER BY started DESC LIMIT 20"):
            if not args.run_id or row["run_id"] == args.run_id:
                print(dict(row), store.run_cost(row["run_id"]))
        for it in actions.list_all(store, args.run_id):
            print(" action", it["key"], it["status"], it.get("approved_by") or "", it.get("done_at") or "")
        return 0
    if args.cmd == "ledger":
        rows = store.q("SELECT ts, run_id, step, endpoint, credits, inr, cache_hit, status FROM ledger "
                       + ("WHERE run_id=? " if args.run_id else "") + "ORDER BY id", *([args.run_id] if args.run_id else []))
        for x in rows:
            print(dict(x))
        print("total", store.run_cost(args.run_id) if args.run_id else store.total_cost())
        return 0
    if args.cmd == "forget":
        from .facts import forget, normalize_url
        print(json.dumps(forget(store, h(normalize_url(args.profile_url))), indent=1)); return 0
    if args.cmd == "sandbox":
        from .sandbox import serve
        print("sandbox receiver on http://127.0.0.1:8765 (records every delivery, duplicates included)")
        serve(); return 0
    if args.cmd == "serve":
        from .api import serve
        serve(args.port); return 0
    if args.cmd in ("watch-create", "watch-register", "watch-pull"):
        from . import watch
        from .crust import Crust
        if args.cmd == "watch-register":
            print(watch.register(store, args.watch_id, args.profile_url)); return 0
        c = Crust(store, f"watch-{args.cmd}", "watch", mode=args.mode)
        if args.cmd == "watch-create":
            print(json.dumps(watch.create(store, c, args.profile_url), indent=1)); return 0
        out = watch.pull(store, c, args.watch_id, args.since, args.as_of, f"watch-{args.watch_id}")
        print(json.dumps(out, indent=1, default=str)); return 0 if "error" not in out else 1
    if args.cmd == "smoke":
        from .crust import Crust
        from .peers import base_filter, count, phrase_cond
        from .config import load_rules
        rules = load_rules()
        c = Crust(store, "smoke", "smoke", mode=args.mode, credit_cap=2)
        c.use_cache = False  # really ask Crustdata
        tot, e1, ts = count(c, base_filter("2026-09-01", rules))
        hi, e2, _ = count(c, base_filter("2026-09-01", rules, phrase_cond("health insurance")))
        print(json.dumps({"logistics_posts_india_since_2026_09_01": tot, "with_health_insurance": hi,
                          "retrieved_at": ts, "errors": [e1, e2], "cost": store.run_cost("smoke")}))
        return 0 if tot and hi is not None else 1
    return 1


if __name__ == "__main__":
    sys.exit(main())
