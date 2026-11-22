"""Kill test: 20 trials. Each trial runs the request under --chaos (random os._exit at step boundaries
and inside the send) until it finishes, approves TWICE (double click), then sends under --chaos until
done. The sandbox records every delivery including duplicates; each trial must show exactly one."""
import json
import os
import socket
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

from conftest import free_port

ROOT = Path(__file__).resolve().parents[1]
TRIALS = int(os.environ.get("BD_CHAOS_TRIALS", "20"))


def bd(*args, env):
    return subprocess.run([sys.executable, "-m", "bd", *args], cwd=ROOT, env=env, capture_output=True, text=True)


def start_sandbox(sd):
    port = free_port()
    proc = subprocess.Popen([sys.executable, "-m", "bd", "sandbox"], cwd=ROOT,
                            env={**os.environ, "BD_STATE_DIR": str(sd), "BD_SANDBOX_PORT": str(port)},
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    for _ in range(50):
        try:
            socket.create_connection(("127.0.0.1", port), 0.2).close(); break
        except OSError:
            time.sleep(0.1)
    return proc, f"http://127.0.0.1:{port}"


def test_kill_test_exactly_once(tmp_path):
    kills, delivered = 0, 0
    for t in range(TRIALS):
        sd = tmp_path / f"trial{t}"
        sd.mkdir()
        proc, sandbox = start_sandbox(sd)  # each trial: fresh state and its own sandbox inbox
        env = {**os.environ, "BD_STATE_DIR": str(sd), "BD_MODE": "replay", "BD_CHAOS_P": "0.35",
               "BD_SANDBOX_URL": sandbox}
        for _ in range(60):  # run until finished; each kill is a restart
            r = bd("run", "requests/T1_job_change.json", "--run-id", f"T1-trial{t}", "--chaos", "--json", env=env)
            if r.returncode == 0:
                break
            assert r.returncode == 137, r.stderr[-2000:]
            kills += 1
        case = json.loads(r.stdout)
        key = case["actions"][0]["key"]
        assert json.loads(bd("approve", key, "--by", "tester", env=env).stdout)["approved"] is True
        assert json.loads(bd("approve", key, "--by", "tester", env=env).stdout)["already"] is True  # double click
        for _ in range(60):
            r = bd("act", f"T1-trial{t}", "--chaos", env=env)
            if r.returncode == 0 and '"done"' in r.stdout:
                break
            kills += r.returncode == 137
        with urllib.request.urlopen(f"{sandbox}/inbox") as resp:
            got = json.loads(resp.read())
        proc.kill()
        assert len(got) == 1 and got[0]["key"] == key and got[0]["count"] == 1, f"trial {t}: {got}"
        delivered += 1
    print(f"\nkill test: {TRIALS} trials, {kills} kills, {delivered} deliveries, 0 duplicates")
