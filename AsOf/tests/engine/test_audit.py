"""Audit verdict rules: date window, tolerance, growth claims."""
from __future__ import annotations

from datetime import date, datetime, timezone

import pytest

from backend.engine import audit_claim, audit_claim_full
from backend.models import ClaimInput
from tests.engine.conftest import base_record

T = datetime(2024, 6, 1, 12, 0, tzinfo=timezone.utc)


def claim(field, value=None, as_of=None, cid="k1"):
    return ClaimInput(id=cid, text=f"{field} is {value}", field=field, value=value, as_of=as_of)


@pytest.mark.parametrize("value,verdict", [(120, "agree"), (150, "agree"), (151, "contradict"), (89, "contradict")])
def test_headcount_tolerance(cfg, value, verdict):
    v = audit_claim(base_record(), claim("headcount", value, date(2024, 3, 1)), T, cfg)
    assert v.verdict == verdict
    assert all(f"[{e}" in v.reason or f", {e}" in v.reason for e in v.line.evidence_ids)


def test_contradict_needs_date_window(cfg):
    # claim dated 15 days after the nearest point: the line is STALE, so no verdict
    v = audit_claim(base_record(), claim("headcount", 999, date(2024, 3, 16)), T, cfg)
    assert v.verdict == "cannot_verify"


def test_undated_claim_cannot_verify(cfg):
    v = audit_claim(base_record(), claim("headcount", 999), T, cfg)
    assert v.verdict == "cannot_verify"


@pytest.mark.parametrize("field", ["headcount_growth", "revenue_growth", "headcount_ratio", "hiring_rate"])
def test_ratio_claims_cannot_verify(cfg, field):
    v, ev = audit_claim_full(base_record(), claim(field, "4x", date(2024, 3, 1)), T, cfg)
    assert v.verdict == "cannot_verify" and v.line.value is None
    if field.startswith(("headcount", "revenue")):
        assert len(v.line.evidence_ids) == 2 and len(ev) == 2


def test_growth_claim_both_values(cfg):
    v = audit_claim(base_record(), claim("headcount_growth", "20%"), T, cfg)
    assert "2024-01-01" in v.reason and "employee_count 100" in v.reason
    assert "2024-03-01" in v.reason and "employee_count 120" in v.reason


def test_revenue_band_audit(cfg):
    d = date(2024, 2, 1)
    assert audit_claim(base_record(), claim("revenue_band", 3_000_000, d), T, cfg).verdict == "agree"
    assert audit_claim(base_record(), claim("revenue_band", 50_000_000, d), T, cfg).verdict == "contradict"
    assert audit_claim(base_record(), claim("revenue_band", 5_500_000, d), T, cfg).verdict == "cannot_verify"


def test_listing_audit_never_asserts_not_listed(cfg):
    assert audit_claim(base_record(), claim("listing", "listed", date(2021, 1, 1)), T, cfg).verdict == "agree"
    # before IPO: the record can't attest, so a "not listed" claim is not confirmed
    assert audit_claim(base_record(), claim("listing", "not listed", date(2019, 1, 1)), T, cfg).verdict == "cannot_verify"


def test_existence_audit(cfg):
    assert audit_claim(base_record(), claim("existence", 2010, date(2020, 1, 1)), T, cfg).verdict == "agree"
    assert audit_claim(base_record(), claim("existence", 2005, date(2020, 1, 1)), T, cfg).verdict == "contradict"


def test_domains_audit_absence_is_not_negative(cfg):
    assert audit_claim(base_record(), claim("domains", "acme.test", date(2024, 5, 25)), T, cfg).verdict == "agree"
    assert audit_claim(base_record(), claim("domains", "other.test", date(2024, 5, 25)), T, cfg).verdict == "cannot_verify"


def test_audit_malformed_record(cfg):
    for rec in (None, {}, "garbage"):
        assert audit_claim(rec, claim("headcount", 10, date(2024, 3, 1)), T, cfg).verdict == "cannot_verify"
        v = audit_claim(rec, claim("headcount_growth", "4x"), T, cfg)
        assert v.verdict == "cannot_verify" and v.line.refusal_code == "SOURCE_UNAVAILABLE"
