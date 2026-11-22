import shutil
from pathlib import Path

import pytest

from backend.crust.client import CrustClient
from backend.pipeline import engine_adapter
from backend.pipeline.session import FIXTURE_CACHE, Session, set_session

from .fakes import FAKE


@pytest.fixture(autouse=True)
def env(tmp_path, monkeypatch):
    monkeypatch.setenv("ASOF_STATE_DIR", str(tmp_path / "state"))
    monkeypatch.setenv("ASOF_TODAY", "2026-11-22")
    try:
        import backend.engine as real
        assert all(hasattr(real, n) for n in ("load_config", "attest", "observe", "audit_claim"))
        engine_adapter.set_engine(None)  # use the real engine once it lands
    except (Exception, AssertionError):
        engine_adapter.set_engine(FAKE, {})
    yield
    engine_adapter.set_engine(None)
    set_session(None)


@pytest.fixture
def session(tmp_path):
    client = CrustClient(run_id="t", mode="replay", cache_dir=FIXTURE_CACHE, ledger_dir=tmp_path / "ledger")
    s = Session(client=client)
    set_session(s)
    return s
