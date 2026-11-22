"""Artifact store: drafts persist to state/artifacts so approve/issue work across CLI invocations."""
from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

from backend.models import AuditReport, CaseFile, EvidenceRequest

from .errors import RequestError
from .session import state_dir

_TYPES = {"CaseFile": CaseFile, "AuditReport": AuditReport, "EvidenceRequest": EvidenceRequest}


def _dir() -> Path:
    d = state_dir() / "artifacts"
    d.mkdir(parents=True, exist_ok=True)
    return d


def artifact_id(obj) -> str:
    if isinstance(obj, EvidenceRequest):
        return "ER-" + obj.idempotency_key[:12]
    return obj.id


def save(obj) -> str:
    aid = artifact_id(obj)
    payload = json.dumps({"type": type(obj).__name__, "data": json.loads(obj.model_dump_json())})
    fd, tmp = tempfile.mkstemp(dir=_dir(), suffix=".tmp")
    with os.fdopen(fd, "w") as f:
        f.write(payload)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, _dir() / f"{aid}.json")
    return aid


def load(aid: str):
    if not isinstance(aid, str) or not aid.replace("-", "").isalnum():
        raise RequestError("give a case file, audit report or evidence request id")
    p = _dir() / f"{aid}.json"
    try:
        raw = json.loads(p.read_text())
        return _TYPES[raw["type"]].model_validate(raw["data"])
    except FileNotFoundError:
        raise RequestError(f"no draft with id {aid!r}; create it first") from None
    except Exception:
        raise RequestError(f"draft {aid!r} is unreadable (torn or corrupt file)") from None
