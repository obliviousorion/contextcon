"""Per-run cost ledger (JSONL on disk) + price table."""
from __future__ import annotations

import json
import os
import uuid
from dataclasses import asdict, dataclass
from pathlib import Path

from .cache import DEFAULT_LEDGER_DIR, now_iso


def _credit_to_inr() -> float:
    try:
        from backend.platform.config import credit_to_inr
        return credit_to_inr()
    except Exception:
        return 0.30 * 94.12  # config.yaml unreadable: same values as the shipped config


CREDIT_TO_INR = _credit_to_inr()  # usd_per_credit x inr_per_usd from config.yaml
DEFAULT_CREDIT_CAP = 400.0

# credits per unit; unit counted from response (or request) by Client._units
PRICES = {
    "/company/enrich": 2.0,   # per record
    "/company/identify": 0.2,  # per match (unmatched is free)
    "/company/search": 0.03,  # per result
    "/web/search/live": 1.0,  # per call
    "/web/enrich/live": 1.0,  # per page (measured 2026-11-22: one url, balance -1.0)
}


@dataclass
class LedgerEntry:
    run_id: str
    ts: str
    endpoint: str
    credits: float
    cumulative: float
    cache_hit: bool
    intent_id: str = ""


class Ledger:
    def __init__(self, run_id: str, directory: Path | str | None = None):
        self.run_id = run_id
        self.path = Path(directory or DEFAULT_LEDGER_DIR) / f"{run_id}.jsonl"
        self.entries: list[LedgerEntry] = []
        self._pending: dict[str, float] = {}
        try:
            lines = self.path.read_text().splitlines()
        except OSError:
            lines = []
        for line in lines:
            if not line.strip():
                continue
            try:
                d = json.loads(line)
                if "intent" in d:  # written (fsync) before a network call
                    self._pending[d["id"]] = float(d["intent"])
                elif "released" in d:
                    self._pending.pop(d["released"], None)
                else:
                    e = LedgerEntry(**d)
                    self.entries.append(e)
                    self._pending.pop(e.intent_id, None)
            except (ValueError, TypeError, KeyError, AttributeError):
                continue  # torn/garbage line: skip it, keep the true total from the rest

    @property
    def total(self) -> float:
        """Confirmed credits plus the estimate of any call whose intent has no matching done line
        (a kill mid-call or a torn done line): the cap can overcount, never undercount."""
        return (self.entries[-1].cumulative if self.entries else 0.0) + sum(self._pending.values())

    def _append(self, rec: dict) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        line = json.dumps(rec) + "\n"
        fd = os.open(self.path, os.O_RDWR | os.O_APPEND | os.O_CREAT, 0o644)
        try:
            size = os.fstat(fd).st_size
            if size and os.pread(fd, 1, size - 1) != b"\n":
                line = "\n" + line  # heal torn tail
            os.write(fd, line.encode())
            os.fsync(fd)
        finally:
            os.close(fd)

    def intent(self, endpoint: str, est: float) -> str:
        iid = uuid.uuid4().hex[:12]
        self._pending[iid] = float(est)
        self._append({"intent": float(est), "id": iid, "endpoint": endpoint, "ts": now_iso()})
        return iid

    def release(self, intent_id: str) -> None:
        if self._pending.pop(intent_id, None) is not None:
            self._append({"released": intent_id})

    def add(self, endpoint: str, credits: float, cache_hit: bool, intent_id: str = "") -> LedgerEntry:
        credits = 0.0 if cache_hit else float(credits)
        base = self.entries[-1].cumulative if self.entries else 0.0
        e = LedgerEntry(self.run_id, now_iso(), endpoint, credits, round(base + credits, 6), cache_hit, intent_id)
        self.entries.append(e)
        self._pending.pop(intent_id, None)
        self._append(asdict(e))
        return e


def get_run_cost(run_id: str, directory: Path | str | None = None) -> float:
    return Ledger(run_id, directory).total


def cost_summary(run_id: str, directory: Path | str | None = None):
    """CostSummary (credits, INR, calls, cache hits) for a run, INR from current config."""
    from backend.models import CostSummary
    led = Ledger(run_id, directory)
    calls = sum(1 for e in led.entries if not e.cache_hit)
    hits = sum(1 for e in led.entries if e.cache_hit)
    return CostSummary(credits=led.total, inr=round(led.total * _credit_to_inr(), 2), calls=calls, cache_hits=hits)
