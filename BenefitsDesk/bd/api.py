"""HTTP API + static UI (stdlib only). Each run is a child process (`python -m bd run ...`), so the
Kill button is a real SIGKILL and Resume is a real restart that reuses the step store."""
from __future__ import annotations

import json
import mimetypes
import os
import socket
import subprocess
import sys
import time
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from . import actions
from .config import load_config
from .store import ROOT, Store, h, now, state_dir

DIST = ROOT / "web" / "dist"
PROCS: dict[str, subprocess.Popen] = {}
FILES: dict[str, str] = {}


def _spawn(args: list[str]) -> subprocess.Popen:
    log = open(state_dir() / "runs.log", "ab")
    env = {**os.environ, "BD_STEP_DELAY": str(load_config().get("ui", {}).get("step_delay_seconds", 0))}
    return subprocess.Popen([sys.executable, "-m", "bd", *args], cwd=ROOT, stdout=log, stderr=log, env=env)


class H(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _json(self, obj, code=200):
        b = json.dumps(obj, default=str).encode()
        self.send_response(code)
        self.send_header("content-type", "application/json")
        self.send_header("content-length", str(len(b)))
        self.end_headers()
        self.wfile.write(b)

    def _cookie(self) -> str | None:
        for part in (self.headers.get("cookie") or "").split(";"):
            k, _, v = part.strip().partition("=")
            if k == "bd_session":
                return v
        return None

    def _uid(self) -> str | None:
        from . import users as U
        return U.session_user(Store(), self._cookie())

    def _json_cookie(self, obj, code: int, token: str | None):
        b = json.dumps(obj, default=str).encode()
        self.send_response(code)
        self.send_header("content-type", "application/json")
        self.send_header("content-length", str(len(b)))
        if token is not None:
            age = 0 if token == "" else 7 * 86400
            self.send_header("set-cookie", f"bd_session={token}; HttpOnly; SameSite=Strict; Path=/; Max-Age={age}")
        self.end_headers()
        self.wfile.write(b)

    def _start_guided(self, uid: str) -> str:
        from . import users as U
        cfg = load_config()["guided"]
        req = {"id": "guided", "type": "guided_review", "user_id": uid, "as_of": cfg["as_of"], "since": cfg["since"]}
        d = state_dir() / "requests"; d.mkdir(exist_ok=True)
        rid = f"guided-{uid[:6]}-{h(req, time.time())[:6]}"
        f = str(d / f"{rid}.json"); Path(f).write_text(json.dumps(req)); FILES[rid] = f
        mode = "record" if U.mode_of(Store(), uid) == "live" else "replay"
        s = Store()
        U.save_state(s, uid, last_run_id=rid)
        s.x("INSERT OR IGNORE INTO user_runs VALUES (?,?,?)", uid, rid, now())
        PROCS[rid] = _spawn(["run", f, "--run-id", rid, "--mode", mode])
        return rid

    def _body(self) -> dict:
        n = int(self.headers.get("content-length") or 0)
        return json.loads(self.rfile.read(n) or b"{}") if n else {}

    # ---- GET --------------------------------------------------------------
    def do_GET(self):
        u = urlparse(self.path)
        q = {k: v[0] for k, v in parse_qs(u.query).items()}
        p = u.path
        s = Store()
        if p in ("/api/me", "/api/intake", "/api/dashboard"):
            from . import users as U, guided as G
            uid = self._uid()
            if p == "/api/me":
                if not uid:
                    return self._json({"logged_in": False})
                return self._json({"logged_in": True, "user_id": uid, "stage": U.state(s, uid).get("stage"), "mode": U.mode_of(s, uid)})
            if not uid:
                return self._json({"error": "Please sign in."}, 401)
            if p == "/api/intake":
                items = [i for i in U.state(s, uid).get("intake") or [] if not i.get("hidden")]
                return self._json({"items": items})
            return self._json(G.dashboard(s, uid, q.get("as_of")))
        if p == "/api/requests":
            out = []
            for f in sorted((ROOT / "requests").glob("*.json")):
                r = json.loads(f.read_text())
                out.append({"file": f"requests/{f.name}", "id": r.get("id"), "type": r.get("type"), "said": r.get("said")})
            return self._json(out)
        if p == "/api/runs":
            return self._json([{"run_id": r["run_id"], "request_id": json.loads(r["request"]).get("id"),
                                "type": json.loads(r["request"]).get("type"), "status": self._status(r["run_id"], r["status"]),
                                "started": r["started"], "finished": r["finished"]}
                               for r in s.q("SELECT * FROM runs ORDER BY started DESC")])
        if p.startswith("/api/runs/"):
            rid = p.rsplit("/", 1)[1]
            r = s.q("SELECT * FROM runs WHERE run_id=?", rid)
            if not r:
                return self._json({"error": "no such run"}, 404)
            st = self._status(rid, r[0]["status"])
            if st == "running" or not r[0]["result"]:
                return self._json({"run_id": rid, "status": st})
            return self._json(json.loads(r[0]["result"]))
        if p == "/api/stream":
            return self._stream(q.get("run_id", ""), int(q.get("after", 0)))
        if p == "/api/ledger":
            rid = q.get("run_id")
            rows = s.q("SELECT ts, step, endpoint, credits, inr, cache_hit, status FROM ledger "
                       + ("WHERE run_id=? " if rid else "") + "ORDER BY id", *([rid] if rid else []))
            return self._json({"rows": [dict(x) | {"cache_hit": bool(x["cache_hit"])} for x in rows],
                               "total": s.run_cost(rid) if rid else s.total_cost(),
                               "cap": load_config()["limits"]["credit_cap_per_run"]})
        if p == "/api/approvals":
            return self._json(actions.list_all(s))
        if p == "/api/sandbox":
            try:
                with urllib.request.urlopen(actions._sandbox() + "/inbox", timeout=3) as r:
                    return self._json(json.loads(r.read()))
            except OSError as e:
                return self._json({"error": f"sandbox unreachable: {e}"}, 503)
        if p == "/api/beliefs":
            rows = s.q("SELECT * FROM beliefs WHERE group_key=? ORDER BY belief_key, version", q.get("group", ""))
            return self._json([dict(r) | {"sources": json.loads(r["sources"])} for r in rows])
        return self._static(p)

    def _status(self, rid: str, db_status: str) -> str:
        pr = PROCS.get(rid)
        if pr is not None and pr.poll() is None:
            return "running"
        if db_status == "running":
            return "stopped"  # killed or crashed mid-run: resume continues it
        return db_status

    def _stream(self, rid: str, after: int):
        self.send_response(200)
        self.send_header("content-type", "text/event-stream")
        self.send_header("cache-control", "no-cache")
        self.end_headers()
        s = Store()
        last, idle = after, 0
        try:
            while idle < 600:
                rows = s.q("SELECT * FROM events WHERE run_id=? AND id>? ORDER BY id", rid, last)
                for r in rows:
                    last = r["id"]
                    self.wfile.write(f"id: {r['id']}\ndata: {json.dumps(dict(r))}\n\n".encode())
                self.wfile.flush()
                pr = PROCS.get(rid)
                if not rows and (pr is None or pr.poll() is not None):
                    idle += 5
                    self.wfile.write(b": keepalive\n\n")
                else:
                    idle = 0
                time.sleep(0.25)
        except (BrokenPipeError, ConnectionResetError):
            pass

    def _static(self, p: str):
        f = (DIST / p.lstrip("/")).resolve()
        if not str(f).startswith(str(DIST.resolve())) or not f.is_file():
            f = DIST / "index.html"
        if not f.exists():
            return self._json({"error": "UI not built: cd web && npm install && npm run build"}, 404)
        b = f.read_bytes()
        self.send_response(200)
        self.send_header("content-type", mimetypes.guess_type(str(f))[0] or "application/octet-stream")
        self.send_header("content-length", str(len(b)))
        self.end_headers()
        self.wfile.write(b)

    # ---- POST -------------------------------------------------------------
    def do_POST(self):
        p, b, s = urlparse(self.path).path, self._body(), Store()
        if p in ("/api/login", "/api/logout", "/api/forget", "/api/intake", "/api/answers", "/api/check", "/api/mode", "/api/choose"):
            return self._guided_post(p, b, s)
        if p == "/api/run":
            if b.get("file"):
                f = b["file"]
                req = json.loads((ROOT / f).read_text())
            else:
                req = b["request"]
                d = state_dir() / "requests"; d.mkdir(exist_ok=True)
                f = str(d / f"{h(req)}.json"); Path(f).write_text(json.dumps(req))
            rid = f"{req.get('id', 'run')}-{h(req, time.time())[:6]}"
            FILES[rid] = f
            PROCS[rid] = _spawn(["run", f, "--run-id", rid, *(["--chaos"] if b.get("chaos") else [])])
            return self._json({"run_id": rid})
        if p == "/api/kill":
            pr = PROCS.get(b.get("run_id", ""))
            if pr is None or pr.poll() is not None:
                return self._json({"killed": False})
            pr.kill(); pr.wait()
            s.event(b["run_id"], "run", "killed", "SIGKILL from the console")
            return self._json({"killed": True})
        if p == "/api/resume":
            rid = b["run_id"]
            f = FILES.get(rid)
            if not f:
                r = s.q("SELECT request FROM runs WHERE run_id=?", rid)
                if not r:
                    return self._json({"error": "no such run"}, 404)
                d = state_dir() / "requests"; d.mkdir(exist_ok=True)
                f = str(d / f"{rid}.json"); Path(f).write_text(r[0]["request"]); FILES[rid] = f
            PROCS[rid] = _spawn(["run", f, "--run-id", rid])
            return self._json({"run_id": rid})
        if p == "/api/approve":
            return self._json(actions.approve(s, b["key"], b.get("approver") or "person"))
        if p == "/api/act":
            rid = b["run_id"]
            PROCS[rid] = _spawn(["act", rid])
            return self._json({"run_id": rid})
        if p == "/api/facts":
            s.x("INSERT OR REPLACE INTO facts VALUES (?,?,?,?,?,?,?,?)", b["persona_id"], b["fact_id"],
                f"{b['fact_id']}: {b['value']} (corrected by the person)", json.dumps(b["value"]), "told",
                json.dumps({"record": "the person's own correction", "field_path": f"answers.{b['fact_id']}",
                            "retrieved_at": now(), "record_date": now()}), now(), now())
            return self._json({"saved": True, "label": "told"})
        return self._json({"error": "not found"}, 404)


def _guided_post(self, p: str, b: dict, s: Store):
    from . import users as U, guided as G
    from .crust import Crust
    if p == "/api/login":
        try:
            entry = U.allowlisted(b.get("link"), b.get("name"), b.get("company"))
            uid0 = h(U.normalize_url(entry["profile_url"])) if entry else None
            mode = "record" if (uid0 and U.mode_of(s, uid0) == "live") else "replay"
            res, token = U.login(s, b.get("link"), b.get("name"), b.get("company"), str(b.get("pin") or ""),
                                 bool(b.get("consent")), Crust(s, f"login-{(uid0 or 'x')[:6]}", "intake", mode=mode))
            return self._json_cookie(res, 200, token)
        except U.LoginError as e:
            return self._json({"error": e.msg}, e.code)
    if p == "/api/logout":
        U.logout(s, self._cookie())
        return self._json_cookie({"ok": True}, 200, "")
    uid = self._uid()
    if not uid:
        return self._json({"error": "Please sign in."}, 401)
    try:
        if p == "/api/forget":
            return self._json_cookie(U.forget(s, uid), 200, "")
        if p == "/api/intake":
            return self._json(U.confirm(s, uid, b.get("items") or {}))
        if p == "/api/answers":
            if U.state(s, uid).get("stage") not in ("questions", "dashboard"):
                return self._json({"error": "Please confirm your details first."}, 400)
            U.save_state(s, uid, answers={"dependants": b.get("dependants") or [], "insurance_now": b.get("insurance_now") or []})
            return self._json({"run_id": self._start_guided(uid)})
        if p == "/api/check":
            return self._json({"run_id": self._start_guided(uid)})
        if p == "/api/mode":
            m = b.get("mode")
            if m not in ("live", "replay"):
                return self._json({"error": "mode is live or replay"}, 400)
            s.x("UPDATE users SET mode=? WHERE user_id=?", m, uid)
            return self._json({"mode": m})
        if p == "/api/choose":
            return self._json({"action": G.choose(s, uid, int(b.get("company_id")))})
    except U.LoginError as e:
        return self._json({"error": e.msg}, e.code)
    return self._json({"error": "not found"}, 404)


H._guided_post = _guided_post


def _port_free(port: int) -> bool:
    with socket.socket() as so:
        return so.connect_ex(("127.0.0.1", port)) != 0


def serve(port: int = 8787) -> None:
    sb = urlparse(load_config()["sandbox"]["url"]).port or 8765
    if not os.environ.get("BD_SANDBOX_URL") and _port_free(sb):
        _spawn(["sandbox"])
        print(f"started sandbox receiver on :{sb}")
    print(f"Benefits Desk on http://127.0.0.1:{port}  (API under /api)")
    ThreadingHTTPServer(("127.0.0.1", port), H).serve_forever()
