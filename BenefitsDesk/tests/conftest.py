import os
import socket
import subprocess
import sys
import time
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def state(tmp_path, monkeypatch):
    """Isolated state dir, replay mode: tests never spend credits."""
    monkeypatch.setenv("BD_STATE_DIR", str(tmp_path))
    monkeypatch.setenv("BD_MODE", "replay")
    return tmp_path


def free_port() -> int:
    s = socket.socket(); s.bind(("127.0.0.1", 0)); p = s.getsockname()[1]; s.close(); return p


@pytest.fixture
def sandbox(state, monkeypatch):
    port = free_port()
    env = {**os.environ, "BD_SANDBOX_PORT": str(port)}
    proc = subprocess.Popen([sys.executable, "-m", "bd", "sandbox"], cwd=ROOT, env=env,
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    url = f"http://127.0.0.1:{port}"
    monkeypatch.setenv("BD_SANDBOX_URL", url)
    for _ in range(50):
        try:
            socket.create_connection(("127.0.0.1", port), 0.2).close(); break
        except OSError:
            time.sleep(0.1)
    yield url
    proc.kill()
