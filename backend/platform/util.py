"""Small shared helpers: atomic JSON writes, fsynced appends, retry with backoff."""
from __future__ import annotations

import json
import os
import tempfile
import time
from pathlib import Path
from typing import Any, Callable


def atomic_write_json(path: Path | str, obj: Any) -> None:
    """Write temp file in the same dir, fsync, then os.replace: readers never see a torn file."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=path.name + ".", suffix=".tmp")
    try:
        with os.fdopen(fd, "w") as f:
            json.dump(obj, f, default=str)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def read_json(path: Path | str) -> Any | None:
    """Return parsed JSON, or None if missing/torn/corrupt (never raises)."""
    try:
        return json.loads(Path(path).read_text())
    except (OSError, ValueError):
        return None


def append_jsonl(path: Path | str, obj: Any) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    line = json.dumps(obj, default=str) + "\n"
    fd = os.open(path, os.O_RDWR | os.O_APPEND | os.O_CREAT, 0o644)
    try:
        size = os.fstat(fd).st_size
        if size and os.pread(fd, 1, size - 1) != b"\n":
            line = "\n" + line  # heal a torn tail so this record starts on its own line
        os.write(fd, line.encode())  # single write: O_APPEND keeps lines whole
        os.fsync(fd)
    finally:
        os.close(fd)


def read_jsonl(path: Path | str) -> list[dict]:
    out: list[dict] = []
    try:
        for ln in Path(path).read_text().splitlines():
            try:
                v = json.loads(ln)
                if isinstance(v, dict):
                    out.append(v)
            except ValueError:
                continue  # torn line from a kill mid-write
    except OSError:
        pass
    return out


class SourceUnavailable(Exception):
    refusal_code = "SOURCE_UNAVAILABLE"


def with_retry(fn: Callable[[], Any], *, attempts: int = 3, base_delay: float = 0.5,
               retry_on: tuple = (TimeoutError, ConnectionError, OSError),
               sleep: Callable[[float], None] = time.sleep) -> Any:
    """Retry with exponential backoff; after the last failure raise SourceUnavailable
    (refusal code SOURCE_UNAVAILABLE). Silence is never read as an answer."""
    last: Exception | None = None
    for i in range(attempts):
        try:
            return fn()
        except retry_on as e:
            last = e
            if i < attempts - 1:
                sleep(base_delay * (2 ** i))
    raise SourceUnavailable(f"SOURCE_UNAVAILABLE after {attempts} attempts: {last}")
