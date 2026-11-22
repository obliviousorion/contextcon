"""FROZEN contracts for AsOf. Every module talks to the others only through these types.
Change requests go in NOTES.md; the lead session merges them. See SPEC.md."""
from __future__ import annotations

from datetime import date, datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

# The record types AsOf knows how to attest. Anything else -> NO_RECORD_TYPE.
FieldName = Literal["existence", "listing", "headcount", "revenue_band", "domains"]
LineStatus = Literal["attested", "cannot_attest", "subsequent_event"]
RefusalCode = Literal[
    "CANNOT_RESOLVE",     # several candidates and no domain / unmatched
    "CANNOT_ATTEST",      # the record lacks the field (e.g. year_founded null)
    "NOT_YET_RECORDED",   # no data point on or before D (series starts after D)
    "STALE_DATA",         # nearest point on/before D is older than max_staleness_days
    "BEFORE_FOUNDING",    # D is before the record's founding year
    "FUTURE_DATE",        # D is after the record was retrieved
    "NO_RECORD_TYPE",     # field outside FieldName
    "SOURCE_UNAVAILABLE", # timeout / error / malformed response: never read as an answer
    "BUDGET_HELD",        # run hit its credit or time limit; resumable
]
Label = Literal["profile-derived count", "estimate", "true at retrieval only", "as recorded"]


class Evidence(BaseModel):
    id: str  # "E{n}"
    kind: Literal["company_record", "web_page", "watch_alert"]
    source_endpoint: str  # e.g. "/company/enrich"
    url: str | None = None
    field_path: str | None = None  # e.g. "headcount.timeseries[2024-07-15].employee_count"
    excerpt: str = Field(max_length=400)  # verbatim value or passage
    point_date: date | None = None  # date the data point / page states
    retrieved_at: datetime  # when our stored copy was fetched
    cache_key: str | None = None


class Candidate(BaseModel):
    crustdata_company_id: int
    name: str | None = None
    domains: list[str] = Field(default_factory=list)
    confidence: float | None = None


class Entity(BaseModel):
    crustdata_company_id: int
    name: str | None = None
    domains: list[str] = Field(default_factory=list)
    resolved_by: Literal["domain", "id"]
    evidence_id: str | None = None


class ResolveResult(BaseModel):
    status: Literal["resolved", "cannot_resolve"]
    entity: Entity | None = None
    candidates: list[Candidate] = Field(default_factory=list)
    missing: str | None = None  # what would settle it, e.g. "a domain"


class AttestLine(BaseModel):
    field: str
    as_of: date
    status: LineStatus
    value: Any | None = None
    point_date: date | None = None
    label: Label | None = None
    statement: str  # templated: "Data point dated P states X; stored copy retrieved T." Never "was true on D".
    refusal_code: RefusalCode | None = None
    missing: str | None = None  # names exactly what is missing
    gap_days: int | None = None
    evidence_ids: list[str] = Field(default_factory=list)


class CostSummary(BaseModel):
    credits: float = 0.0
    inr: float = 0.0
    calls: int = 0
    cache_hits: int = 0
    # What the stored copies cost when they were recorded (from the recorded ledger). In replay mode
    # credits/inr are 0 (nothing was spent this run); these show the measured cost of the same file live.
    recorded_credits: float = 0.0
    recorded_inr: float = 0.0


class Attestation(BaseModel):
    entity: Entity
    as_of: date
    lines: list[AttestLine]
    subsequent_events: list[AttestLine] = Field(default_factory=list)  # evidence dated after D, never attested
    generated_at: datetime


class EvidenceRequest(BaseModel):
    """Held request to a counterparty when records can't settle it. Never a rejection."""
    target: str  # domain or name
    items: list[str]  # e.g. ["domain", "GSTIN", "registration documents"]
    note: str = "Not a negative finding."
    status: Literal["draft", "approved", "sent_sandbox"] = "draft"
    idempotency_key: str


class CaseFile(BaseModel):
    """The finished artifact: a clearance file (as of today) or a dispute file (as of a past date)."""
    id: str
    kind: Literal["clearance", "dispute"]
    request: dict[str, Any]
    resolve: ResolveResult
    attestation: Attestation | None = None
    evidence: dict[str, Evidence] = Field(default_factory=dict)
    evidence_request: EvidenceRequest | None = None
    cost: CostSummary = Field(default_factory=CostSummary)
    status: Literal["draft", "approved", "issued_sandbox"] = "draft"
    idempotency_key: str


class ClaimInput(BaseModel):
    id: str
    text: str
    field: str
    value: Any | None = None
    as_of: date | None = None


class ClaimVerdict(BaseModel):
    claim_id: str
    verdict: Literal["agree", "contradict", "cannot_verify"]
    line: AttestLine
    reason: str  # templated, cites line.evidence_ids


class AuditReport(BaseModel):
    id: str
    entity: Entity | None
    verdicts: list[ClaimVerdict]
    status: Literal["draft", "approved", "issued_sandbox"] = "draft"
    idempotency_key: str


class ActionRecord(BaseModel):
    key: str
    action: Literal["issue_case_file", "issue_audit_report", "send_evidence_request", "create_watcher", "exceed_budget"]
    target: str
    status: Literal["pending", "done", "failed"]
    ts: datetime


class LedgerEntry(BaseModel):
    run_id: str
    ts: datetime
    call: str  # endpoint or model name
    credits: float = 0.0
    tokens: int | None = None
    cache_hit: bool = False
    cumulative_credits: float = 0.0
    cumulative_inr: float | None = None


class WatchSnapshot(BaseModel):
    watch_id: str
    crustdata_company_id: int
    field: str
    signal_date: date
    snapshot_hash: str
    dedupe_key: str  # sha(watch_id, company_id, field, signal_date)
    stale_line_ids: list[str] = Field(default_factory=list)


class TraceEvent(BaseModel):
    run_id: str
    ts: datetime
    step: str
    status: Literal["start", "progress", "done", "error", "cache_hit", "held_for_approval"]
    message: str
    data: dict[str, Any] | None = None
