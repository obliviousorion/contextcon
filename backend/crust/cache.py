"""Disk JSON cache. Key sha256(path + canonical body). Never stores non-2xx."""
from __future__ import annotations

import hashlib
import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

HERE = Path(__file__).parent
DEFAULT_CACHE_DIR = HERE / "cache"
DEFAULT_LEDGER_DIR = HERE / "ledger"


def canonical(body: Any) -> str:
    return json.dumps(body, sort_keys=True, separators=(",", ":"), default=str) if body is not None else ""


def cache_key(path: str, body: Any = None) -> str:
    return hashlib.sha256((path + canonical(body)).encode()).hexdigest()


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class DiskCache:
    def __init__(self, directory: Path | str | None = None):
        self.dir = Path(directory or os.environ.get("CRUST_CACHE_DIR") or DEFAULT_CACHE_DIR)

    def _p(self, key: str) -> Path:
        return self.dir / f"{key}.json"

    def get(self, key: str, max_age: float | None = None) -> dict | None:
        try:
            entry = json.loads(self._p(key).read_text())
            if not isinstance(entry, dict) or "response" not in entry:
                return None
        except (OSError, ValueError):
            return None
        if max_age is not None:
            try:
                age = time.time() - datetime.fromisoformat(entry["retrieved_at"]).timestamp()
            except Exception:
                return None
            if age > max_age:
                return None
        return entry

    def put(self, key: str, request: dict, response: Any, status: int) -> dict | None:
        if not (200 <= status < 300):
            return None  # never cache non-2xx
        ts = now_iso()
        entry = {"request": request, "response": response, "status": status, "ts": ts, "retrieved_at": ts}
        self.dir.mkdir(parents=True, exist_ok=True)
        tmp = self._p(key).with_suffix(f".{os.getpid()}.tmp")
        tmp.write_text(json.dumps(entry, default=str))
        os.replace(tmp, self._p(key))
        return entry
