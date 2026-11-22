"""The sandbox receiver: stands in for an insurer's inbox. It records EVERY delivery, duplicates
included (it does not dedupe), so the kill test can prove each key arrived exactly once.
Runs as its own process: `bd sandbox`."""
from __future__ import annotations

import json
import sqlite3
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from .store import now, state_dir


def _db(path: Path | None = None) -> sqlite3.Connection:
    db = sqlite3.connect(path or state_dir() / "sandbox.sqlite", isolation_level=None, timeout=30)
    db.execute("PRAGMA journal_mode=WAL")
    db.execute("CREATE TABLE IF NOT EXISTS inbox (id INTEGER PRIMARY KEY AUTOINCREMENT, key TEXT, action TEXT, "
               "payload TEXT, received_at TEXT)")
    return db


def received(path: Path | None = None) -> list[dict]:
    db = _db(path)
    rows = db.execute("SELECT key, action, MIN(received_at), COUNT(*) FROM inbox GROUP BY key ORDER BY 3 DESC").fetchall()
    return [{"key": k, "action": a, "received_at": t, "count": n} for k, a, t, n in rows]


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):  # quiet; no payloads in logs
        pass

    def _send(self, code: int, obj) -> None:
        b = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("content-type", "application/json")
        self.send_header("content-length", str(len(b)))
        self.end_headers()
        self.wfile.write(b)

    def do_GET(self):
        u = urlparse(self.path)
        if u.path != "/inbox":
            return self._send(404, {})
        key = parse_qs(u.query).get("key", [None])[0]
        if key:
            n = _db().execute("SELECT COUNT(*) FROM inbox WHERE key=?", (key,)).fetchone()[0]
            return self._send(200, {"key": key, "count": n})
        self._send(200, received())

    def do_POST(self):
        if urlparse(self.path).path != "/inbox":
            return self._send(404, {})
        body = json.loads(self.rfile.read(int(self.headers.get("content-length", 0))) or b"{}")
        t = now()
        _db().execute("INSERT INTO inbox (key, action, payload, received_at) VALUES (?,?,?,?)",
                      (body.get("key"), body.get("action"), json.dumps(body.get("payload")), t))
        self._send(200, {"received": True, "key": body.get("key"), "received_at": t,
                         "note": "sandbox only: nothing was sent to a real insurer"})


def serve(port: int | None = None) -> None:
    import os
    port = port or int(os.environ.get("BD_SANDBOX_PORT") or 8765)
    ThreadingHTTPServer(("127.0.0.1", port), Handler).serve_forever()
