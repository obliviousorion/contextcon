"""Load config.yaml (re-read on every call so a live edit takes effect mid-run)."""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[2]


def config_path() -> Path:
    return Path(os.environ.get("ASOF_CONFIG") or ROOT / "config.yaml")


def load_config() -> dict[str, Any]:
    with config_path().open() as f:
        return yaml.safe_load(f) or {}


def require(cfg: dict, *keys: str) -> Any:
    """Index nested config keys; a missing key raises KeyError naming the dotted path."""
    cur: Any = cfg
    for i, k in enumerate(keys):
        if not isinstance(cur, dict) or k not in cur:
            raise KeyError(f"config.yaml is missing required key: {'.'.join(keys[:i + 1])}")
        cur = cur[k]
    return cur


def credit_to_inr(cfg: dict | None = None) -> float:
    cfg = cfg or load_config()
    return float(require(cfg, "cost", "usd_per_credit")) * float(require(cfg, "cost", "inr_per_usd"))


def limits(cfg: dict | None = None) -> tuple[float, float]:
    cfg = cfg or load_config()
    return float(require(cfg, "limits", "credit_cap_per_run")), float(require(cfg, "limits", "time_limit_seconds"))


def state_dir() -> Path:
    p = Path(os.environ.get("ASOF_STATE_DIR") or ROOT / "state")
    p.mkdir(parents=True, exist_ok=True)
    return p
