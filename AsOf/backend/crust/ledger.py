"""Per-run cost ledger (JSONL on disk) + price table."""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path

from .cache import DEFAULT_LEDGER_DIR, now_iso


def _credit_to_inr() -> float:
    try:
        from backend.platform.config import credit_to_inr
        return credit_to_inr()
    except Exception:
        return 0.30 * 88  # config.yaml unreadable: same defaults as the shipped config


CREDIT_TO_INR = _credit_to_inr()  # usd_per_credit x inr_per_usd from config.yaml
DEFAULT_CREDIT_CAP = 400.0

# credits per unit; unit counted from response (or request) by Client._units
PRICES = {
    "/company/enrich": 2.0,   # per record
    "/person/enrich": 1.0,    # per profile
    "/company/search": 0.03,  # per result
    "/person/search": 0.03,   # per result
    "/web/search/live": 1.0,  # per call
}


@dataclass
class LedgerEntry:
    run_id: str
    ts: str
    endpoint: str
    credits: float
    cumulative: float
    cache_hit: bool


class Ledger:
    def __init__(self, run_id: str, directory: Path | str | None = None):
        self.run_id = run_id
        self.path = Path(directory or DEFAULT_LEDGER_DIR) / f"{run_id}.jsonl"
        self.entries: list[LedgerEntry] = []
        try:
            for line in self.path.read_text().splitlines():
                if line.strip():
                    self.entries.append(LedgerEntry(**json.loads(line)))
        except (OSError, ValueError, TypeError):
            pass

    @property
    def total(self) -> float:
        return self.entries[-1].cumulative if self.entries else 0.0

    def add(self, endpoint: str, credits: float, cache_hit: bool) -> LedgerEntry:
        credits = 0.0 if cache_hit else float(credits)
        e = LedgerEntry(self.run_id, now_iso(), endpoint, credits, round(self.total + credits, 6), cache_hit)
        self.entries.append(e)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a") as f:
            f.write(json.dumps(asdict(e)) + "\n")
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
