"""AsOf attestation engine: pure functions, no network (SPEC section 3).

Public interface (asof-pipeline codes against this):
    load_config(path="config.yaml") -> dict
    attest(record, field, as_of, retrieved_at, config, evidence_prefix="E")
        -> (AttestLine, list[AttestLine] subsequent_events, list[Evidence])
    observe(record, field, d1, d2, retrieved_at, config) -> (AttestLine, AttestLine)
    observe_full(...) -> (AttestLine, AttestLine, list[Evidence])
    audit_claim(record, claim, retrieved_at, config) -> ClaimVerdict
    audit_claim_full(..., evidence_prefix="E") -> (ClaimVerdict, list[Evidence])
    retrieved_at_from_envelope(envelope) -> datetime | None
"""
from backend.engine.config import load_config
from backend.engine.rules import (
    FORBIDDEN_PHRASE,
    attest,
    audit_claim,
    audit_claim_full,
    is_ratio_field,
    observe,
    observe_full,
    retrieved_at_from_envelope,
)

__all__ = [
    "FORBIDDEN_PHRASE",
    "attest",
    "audit_claim",
    "audit_claim_full",
    "is_ratio_field",
    "load_config",
    "observe",
    "observe_full",
    "retrieved_at_from_envelope",
]
