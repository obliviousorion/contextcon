"""Hidden cases C01-C07 and C09-C16 against the recorded fixtures (C08 and C17 are resolver cases)."""
from __future__ import annotations

from datetime import date

import pytest

from backend.engine import attest, audit_claim
from backend.models import ClaimInput
from tests.engine.conftest import hidden_cases

CASES = hidden_cases()
ATTEST_IDS = ["C01", "C02", "C03", "C04", "C05", "C06", "C07", "C09", "C10", "C11", "C12", "C13", "C14", "C15"]


@pytest.mark.parametrize("cid", ATTEST_IDS)
def test_attest_case(cid, cfg, retrieved_at, record_for):
    case = CASES[cid]
    req, exp = case["request"], case["expected"]
    assert req["tool"] == "attest"
    line, subs, evidence = attest(record_for(req["domain"]), req["field"], date.fromisoformat(req["as_of"]),
                                  retrieved_at, cfg)
    assert line.status == exp["status"], line
    if "refusal_code" in exp:
        assert line.refusal_code == exp["refusal_code"]
        assert line.missing, "every refusal names what is missing"
    if "value" in exp:
        assert line.value == exp["value"]
    if "must_not_equal" in exp:
        assert line.value != exp["must_not_equal"]
    if "point_date" in exp:
        assert line.point_date == date.fromisoformat(exp["point_date"])
    if "label" in exp:
        assert line.label == exp["label"]
    if "missing_mentions" in exp:
        assert exp["missing_mentions"] in line.missing
    if "nearest_point_date" in exp:
        assert exp["nearest_point_date"] in line.missing
        assert line.point_date == date.fromisoformat(exp["nearest_point_date"])
    if "gap_days" in exp:
        assert line.gap_days == exp["gap_days"]
    if "value_contains" in exp:
        for v in exp["value_contains"]:
            assert v in line.value
    # cited: every evidence id on a line exists in the returned evidence
    ev_ids = {e.id for e in evidence}
    for l in [line, *subs]:
        assert set(l.evidence_ids) <= ev_ids
    if line.status == "attested":
        assert line.evidence_ids
    assert all(s.status == "subsequent_event" for s in subs)


def test_c16_growth_claim_cannot_verify(cfg, retrieved_at, record_for):
    case = CASES["C16"]
    c = case["request"]["claims"][0]
    claim = ClaimInput(id=c["id"], text=c["text"], field=c["field"])
    v = audit_claim(record_for(case["request"]["domain"]), claim, retrieved_at, cfg)
    assert v.verdict == "cannot_verify"
    assert v.line.value is None  # never a ratio
    assert len(v.line.evidence_ids) == 2
    # both dated values side by side: TCI's first point and latest point on/before retrieval
    assert "2019-10-28" in v.reason and "employee_count 416" in v.reason
    assert "2026-11-02" in v.reason and "employee_count 1773" in v.reason
    for eid in v.line.evidence_ids:
        assert f"[{eid}]" in v.reason
