"""Config loading for the engine. The only I/O the engine does."""
from __future__ import annotations

from pathlib import Path
from typing import Any


def load_config(path: str | Path = "config.yaml") -> dict[str, Any]:
    """Load config.yaml with yaml.safe_load. Relative paths are tried against the CWD,
    then against the repo root (two levels above this package)."""
    import yaml  # lazy: keeps the rule functions importable without pyyaml

    p = Path(path)
    if not p.is_absolute() and not p.exists():
        alt = Path(__file__).resolve().parents[2] / p
        if alt.exists():
            p = alt
    with p.open("r", encoding="utf-8") as fh:
        cfg = yaml.safe_load(fh)
    if not isinstance(cfg, dict):
        raise ValueError(f"config at {p} is not a mapping")
    return cfg
