"""Single seam to the engine. Real code imports backend.engine; tests may inject a fake via set_engine()."""
from __future__ import annotations

from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
_engine: Any = None
_config: Any = None


def set_engine(engine: Any, config: Any = None) -> None:
    global _engine, _config
    _engine, _config = engine, config


def engine() -> Any:
    global _engine
    if _engine is None:
        import backend.engine as eng  # noqa: PLC0415
        _engine = eng
    return _engine


def config() -> Any:
    global _config
    if _config is None:
        _config = engine().load_config(ROOT / "config.yaml")
    return _config
