"""Per-process session: Crust client, domain->entity cache, record cache, replay fallback index."""
from __future__ import annotations

import json
import os
import uuid
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any

from backend.crust.client import CrustClient
from backend.crust.results import CrustResult
from backend.models import CostSummary, Entity

ROOT = Path(__file__).resolve().parents[2]
FIXTURE_CACHE = ROOT / "fixtures" / "live_check" / "cache"


def state_dir() -> Path:
    return Path(os.environ.get("ASOF_STATE_DIR") or ROOT / "state")


def today() -> date:
    v = os.environ.get("ASOF_TODAY")
    return date.fromisoformat(v) if v else date.today()


def load_yaml() -> dict:
    from backend.platform.config import load_config  # config.yaml is the only source of thresholds
    return load_config()


def parse_ts(s: str | None) -> datetime | None:
    if not s:
        return None
    try:
        return datetime.fromisoformat(s)
    except ValueError:
        return None


# credits per unit proven by the recorded ledger fixtures/live_check/ledger/datacheck-asof.jsonl
RECORDED_UNIT_CREDITS = {"identify": 0.2, "enrich": 2.0}


@dataclass
class Record:
    data: dict
    retrieved_at: datetime
    cache_key: str | None


class ReplayIndex:
    """Fallback for replay mode: the recorded cache holds batched requests, so a single-domain or
    single-id request misses by key. Look the company up in any recorded response instead.
    Never used outside replay; never touches the network."""

    def __init__(self, directory: Path):
        self.by_id: dict[int, tuple[dict, str | None, str]] = {}
        self.by_domain: dict[str, int] = {}
        for f in sorted(directory.glob("*.json")):
            try:
                e = json.loads(f.read_text())
                path = e["request"]["path"]
                if path not in ("/company/identify", "/company/enrich") or not isinstance(e["response"], list):
                    continue
                for item in e["response"]:
                    if item.get("match_type") == "name":
                        continue  # name matches are lookalikes, never a domain mapping
                    for m in item.get("matches") or []:
                        cd = m["company_data"]
                        cid = int(cd["crustdata_company_id"])
                        prev = self.by_id.get(cid)
                        if prev is None or ("headcount" in cd and "headcount" not in prev[0]):
                            self.by_id[cid] = (cd, e.get("retrieved_at"), f.stem)
                for item in e["response"]:
                    # index only the domain identify was actually asked about, and only when it matched
                    # exactly one company: an all_domains alias is not proof (live drl.aero matched two)
                    ms = item.get("matches") or []
                    on = str(item.get("matched_on") or "").lower()
                    ids = {int(m["company_data"]["crustdata_company_id"]) for m in ms}
                    if item.get("match_type") == "domain" and on and len(ids) == 1:
                        self.by_domain.setdefault(on, ids.pop())
            except Exception:
                continue

    def company_for_domain(self, d: str):
        cid = self.by_domain.get(d)
        return (cid, self.by_id[cid]) if cid is not None else None


class Session:
    def __init__(self, client: CrustClient | None = None, run_id: str | None = None):
        self.cfg = load_yaml()
        if client is None:
            limits = self.cfg.get("limits", {})
            cache_dir = os.environ.get("CRUST_CACHE_DIR") or FIXTURE_CACHE
            client = CrustClient(run_id=run_id or f"run-{uuid.uuid4().hex[:8]}",
                                 mode=os.environ.get("MODE") or "replay",
                                 cache_dir=cache_dir, ledger_dir=state_dir() / "ledger",
                                 credit_cap=float(limits.get("credit_cap_per_run", 40)),
                                 time_limit=float(limits.get("time_limit_seconds", 300)))
        self.client = client
        self.entities: dict[str, Entity] = {}          # identified domain -> Entity (never a bare alias)
        self.entity_by_id: dict[int, Entity] = {}      # one record per company, whatever domain found it
        self.entity_evidence: dict[int, dict] = {}     # id -> evidence fields for the identification
        self.records: dict[int, Record] = {}
        self.served = {"identify": 0, "enrich": 0}  # stored copies served (counted once per query)
        self.index = ReplayIndex(Path(client.cache.dir)) if client.mode == "replay" else None

    # --- ledger -------------------------------------------------------------
    def use_run(self, run_id: str) -> None:
        """Bind the client to the ledger file of this request's stable run_id, so a kill and restart reads
        the same ledger (the credit cap counts prior spend; nothing is double counted)."""
        from backend.crust.ledger import Ledger
        led = getattr(self.client, "ledger", None)
        path = getattr(led, "path", None)
        if path is None or not isinstance(led, Ledger):
            return
        self.client.run_id = run_id
        self.client.ledger = Ledger(run_id, path.parent)

    def ledger_mark(self) -> int:
        return len(self.client.ledger.entries)

    def served_mark(self) -> dict:
        return dict(self.served)

    def cost_since(self, mark: int, served0: dict | None = None, extra_served: dict | None = None) -> CostSummary:
        """credits/inr/calls: what THIS run spent (ledger). recorded_*: what the stored copies served cost
        when recorded (units proven by fixtures/live_check/ledger: identify 0.2, enrich 2.0, autocomplete 0)."""
        from backend.crust.ledger import CREDIT_TO_INR
        es = self.client.ledger.entries[mark:]
        credits = round(sum(e.credits for e in es if not e.cache_hit), 6)
        sv = {k: self.served[k] - (served0 or {}).get(k, 0) + (extra_served or {}).get(k, 0) for k in self.served}
        rec = round(sum(sv[k] * RECORDED_UNIT_CREDITS[k] for k in sv), 6)
        return CostSummary(credits=credits, inr=round(credits * CREDIT_TO_INR, 2),
                           calls=sum(1 for e in es if not e.cache_hit), cache_hits=sum(sv.values()),
                           recorded_credits=rec, recorded_inr=round(rec * CREDIT_TO_INR, 2))

    # --- crust with replay fallback ------------------------------------------
    async def identify_domain(self, domain: str) -> CrustResult:
        res = await self.client.company_identify({"domains": [domain]})
        if res.ok and res.cache_hit:
            self.served["identify"] += 1
        if res.ok or self.index is None or res.kind != "replay_miss":
            return res
        hit = self.index.company_for_domain(domain)
        data = [] if hit is None else [{"matched_on": domain, "match_type": "domain", "matches": [
            {"confidence_score": 1.0, "company_data": hit[1][0]}]}]
        if hit is not None:
            self.served["identify"] += 1
        key = None if hit is None else hit[1][2]
        ts = None if hit is None else hit[1][1]
        return CrustResult(ok=True, data=data, retrieved_at=ts, cache_hit=True, cache_key=key,
                           endpoint="/company/identify", extra={"replay_index": True, "recorded": hit is not None})

    async def fetch_record(self, company_id: int) -> tuple[Record | None, CrustResult | None]:
        """Returns (record, None) or (None, failed_result)."""
        if company_id in self.records:
            return self.records[company_id], None
        res = await self.client.company_enrich({"crustdata_company_ids": [company_id],
                                                "fields": ["basic_info", "headcount", "revenue"]})
        cd = _first_company(res.data) if res.ok else None
        key, ts = res.cache_key, res.retrieved_at
        if cd is not None and res.cache_hit:
            self.served["enrich"] += 1
        if not res.ok and self.index is not None and res.kind == "replay_miss":
            hit = self.index.by_id.get(company_id)
            if hit is not None and "headcount" in hit[0]:
                cd, ts, key = hit[0], hit[1], hit[2]
                self.served["enrich"] += 1
        if cd is None:
            return None, res
        when = parse_ts(ts)
        if when is None:
            return None, CrustResult(ok=False, kind="unavailable", reason="response lacks retrieved_at",
                                     endpoint="/company/enrich")
        rec = Record(cd, when, key)
        self.records[company_id] = rec
        return rec, None


def _first_company(data: Any) -> dict | None:
    if isinstance(data, list):
        for item in data:
            for m in (item or {}).get("matches") or []:
                cd = (m or {}).get("company_data")
                if isinstance(cd, dict):
                    return cd
    return None


_session: Session | None = None


def get_session() -> Session:
    global _session
    if _session is None:
        _session = Session()
    return _session


def set_session(s: Session | None) -> None:
    global _session
    _session = s
