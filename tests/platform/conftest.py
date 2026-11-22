import pytest


@pytest.fixture(autouse=True)
def state(tmp_path, monkeypatch):
    monkeypatch.setenv("ASOF_STATE_DIR", str(tmp_path / "state"))
    monkeypatch.delenv("SANDBOX_WEBHOOK_URL", raising=False)
    return tmp_path / "state"
