"""Load config.yaml and rules.yaml. Paths can be overridden for drills and tests."""
from __future__ import annotations

import os
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]


def load_config() -> dict:
    return yaml.safe_load(Path(os.environ.get("BD_CONFIG") or ROOT / "config.yaml").read_text())


def load_rules() -> dict:
    return yaml.safe_load(Path(os.environ.get("BD_RULES") or ROOT / "rules.yaml").read_text())
