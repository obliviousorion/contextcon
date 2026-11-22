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


def credit_to_inr(cfg: dict | None = None) -> float:
    c = (cfg or load_config()).get("cost", {})
    return float(c["usd_per_credit"]) * float(c["inr_per_usd"])


def limits(cfg: dict | None = None) -> tuple[float, float]:
    l = (cfg or load_config()).get("limits", {})
    return float(l.get("credit_cap_per_run", 40)), float(l.get("time_limit_seconds", 300))


def state_dir() -> Path:
    p = Path(os.environ.get("ASOF_STATE_DIR") or ROOT / "state")
    p.mkdir(parents=True, exist_ok=True)
    return p
