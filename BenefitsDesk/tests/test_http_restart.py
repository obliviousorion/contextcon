"""A real server stop and start: the person comes back with link + PIN and lands on the same dashboard,
the cookie survives, and the return makes zero Crustdata calls."""
import json
import os
import socket
import sqlite3
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

from conftest import free_port

ROOT = Path(__file__).resolve().parents[1]
A = "https://www.linkedin.com/in/saanvimittal/"


def start(sd, port):
    env = {**os.environ, "BD_STATE_DIR": str(sd), "BD_MODE": "replay", "BD_SANDBOX_URL": "http://127.0.0.1:9"}
    p = subprocess.Popen([sys.executable, "-c", f"from bd.api import serve; serve({port})"], cwd=ROOT, env=env,
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    for _ in range(100):
        try:
            socket.create_connection(("127.0.0.1", port), 0.2).close(); break
        except OSError:
            time.sleep(0.1)
    return p


def call(port, path, body=None, cookie=None):
    req = urllib.request.Request(f"http://127.0.0.1:{port}{path}", method="POST" if body is not None else "GET",
                                 data=json.dumps(body).encode() if body is not None else None,
                                 headers={"content-type": "application/json", **({"cookie": cookie} if cookie else {})})
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            return r.status, json.loads(r.read()), r.headers.get("set-cookie")
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read()), None


def test_details_survive_a_real_server_restart(tmp_path):
    sd = tmp_path / "state"; sd.mkdir()
    port = free_port()
    srv = start(sd, port)
    try:
        code, res, sc = call(port, "/api/login", {"link": A, "pin": "2468", "consent": True})
        assert code == 200 and res["stage"] == "confirm"
        cookie = sc.split(";")[0]
        assert "HttpOnly" in sc
        _, intake, _ = call(port, "/api/intake", cookie=cookie)
        dec = {i["key"]: ({"action": "confirm"} if i["kind"] != "missing" else {"action": "edit", "value": "Pilani"}) for i in intake["items"]}
        assert call(port, "/api/intake", {"items": dec}, cookie)[1]["stage"] == "questions"
        _, r, _ = call(port, "/api/answers", {"dependants": ["just_me"], "insurance_now": ["none"]}, cookie)
        for _ in range(200):
            _, d, _ = call(port, "/api/dashboard", cookie=cookie)
            if d["run"]["status"] not in ("running", "none"):
                break
            time.sleep(0.2)
        assert d["run"]["status"] == "finished" and d["profile"] and len(d["trail"]) == 5
    finally:
        srv.kill(); srv.wait()
    ledger_before = sqlite3.connect(sd / "desk.sqlite").execute("SELECT COUNT(*) FROM ledger").fetchone()[0]
    srv = start(sd, port)                                    # full stop and start
    try:
        assert call(port, "/api/me", cookie=cookie)[1]["logged_in"] is True          # a refresh keeps you signed in
        code, again, _ = call(port, "/api/login", {"link": A, "pin": "2468", "consent": False})
        assert code == 200 and again["returning"] is True and again["stage"] == "dashboard"
        _, d2, _ = call(port, "/api/dashboard", cookie=cookie)
        for k in ("profile", "gaps", "trail", "diary"):
            assert d2[k] == d[k]
        code, bad, _ = call(port, "/api/login", {"link": A, "pin": "1111", "consent": False})
        assert code == 401 and "Saanvi" not in json.dumps(bad)
    finally:
        srv.kill(); srv.wait()
    assert sqlite3.connect(sd / "desk.sqlite").execute("SELECT COUNT(*) FROM ledger").fetchone()[0] == ledger_before
