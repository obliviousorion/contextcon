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


class ConfigKeyError(KeyError):
    """A required config key is missing; the message names the dotted key."""

    def __str__(self) -> str:  # KeyError would repr() the message; keep it readable
        return str(self.args[0]) if self.args else "missing config key"


def require(config: Any, dotted: str) -> Any:
    """Index config by a dotted key (e.g. 'attest.max_staleness_days') with no fallback.
    Raises ConfigKeyError naming the full key when any part is missing."""
    node = config
    for part in dotted.split("."):
        if not isinstance(node, dict) or part not in node or node[part] is None:
            raise ConfigKeyError(f"missing required config key '{dotted}' (check config.yaml)")
        node = node[part]
    return node
