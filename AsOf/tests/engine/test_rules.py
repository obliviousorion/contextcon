"""A pass and a fail fixture per field rule, plus the cross-field rules."""
from __future__ import annotations

import copy
from datetime import date, datetime, timezone

import pytest

from backend.engine import attest, observe, observe_full
from tests.engine.conftest import base_record

T = datetime(2024, 6, 1, 12, 0, tzinfo=timezone.utc)


# ---- headcount
def test_headcount_pass(cfg):
    line, subs, ev = attest(base_record(), "headcount", date(2024, 2, 10), T, cfg)
    assert (line.status, line.value, line.point_date) == ("attested", 110, date(2024, 2, 1))
    assert line.label == cfg["attest"]["labels"]["headcount"]
    assert ev[0].field_path == "headcount.timeseries[2024-02-01].employee_count"
    assert ev[0].source_endpoint == "/company/enrich"
    assert [s.point_date for s in subs] == [date(2024, 3, 1)]


def test_headcount_fail_not_yet_recorded(cfg):
    line, subs, _ = attest(base_record(), "headcount", date(2023, 12, 1), T, cfg)
    assert line.refusal_code == "NOT_YET_RECORDED"
    assert "2024-01-01" in line.missing
    assert line.value is None


def test_headcount_fail_missing_series(cfg):
    line, _, _ = attest(base_record(headcount=None), "headcount", date(2024, 2, 1), T, cfg)
    assert line.refusal_code == "CANNOT_ATTEST" and "headcount.timeseries" in line.missing


def test_headcount_null_value_point_is_not_attested(cfg):
    rec = base_record()
    rec["headcount"]["timeseries"][1]["employee_count"] = None
    line, _, _ = attest(rec, "headcount", date(2024, 2, 5), T, cfg)
    assert line.status == "cannot_attest" and line.refusal_code == "CANNOT_ATTEST"
    assert "2024-02-01" in line.missing


# ---- staleness boundary
@pytest.mark.parametrize("days,status", [(14, "attested"), (15, "cannot_attest")])
def test_staleness_boundary(cfg, days, status):
    rec = base_record()
    as_of = date(2024, 3, 1).fromordinal(date(2024, 3, 1).toordinal() + days)
    line, _, _ = attest(rec, "headcount", as_of, T, cfg)
    assert line.status == status
    if status == "attested":
        assert line.value == 120 and line.refusal_code is None
    else:
        assert line.refusal_code == "STALE_DATA" and line.gap_days == 15
        assert "2024-03-01" in line.missing and line.point_date == date(2024, 3, 1)


def test_staleness_reads_config(cfg):
    c = copy.deepcopy(cfg)
    c["attest"]["max_staleness_days"] = 20
    line, _, _ = attest(base_record(), "headcount", date(2024, 3, 16), T, c)
    assert line.status == "attested"


def test_revenue_staleness_boundary(cfg):
    ok, _, _ = attest(base_record(), "revenue_band", date(2024, 2, 15), T, cfg)
    stale, _, _ = attest(base_record(), "revenue_band", date(2024, 2, 16), T, cfg)
    assert ok.status == "attested" and stale.refusal_code == "STALE_DATA" and stale.gap_days == 15


# ---- existence
def test_existence_pass(cfg):
    line, _, ev = attest(base_record(), "existence", date(2015, 1, 1), T, cfg)
    assert (line.status, line.value) == ("attested", 2010)
    assert ev[0].field_path == "basic_info.year_founded"


def test_existence_fail_before_founding(cfg):
    line, _, _ = attest(base_record(), "existence", date(2009, 12, 31), T, cfg)
    assert line.refusal_code == "BEFORE_FOUNDING" and "2010" in line.missing


def test_existence_fail_no_year(cfg):
    rec = base_record()
    rec["basic_info"]["year_founded"] = None
    line, _, _ = attest(rec, "existence", date(2015, 1, 1), T, cfg)
    assert line.refusal_code == "CANNOT_ATTEST" and "year_founded" in line.missing


# ---- listing
def test_listing_pass(cfg):
    line, _, _ = attest(base_record(), "listing", date(2020, 6, 15), T, cfg)
    assert (line.status, line.value, line.point_date) == ("attested", "listed", date(2020, 6, 15))


def test_listing_fail_ipo_after_d(cfg):
    line, subs, _ = attest(base_record(), "listing", date(2020, 6, 14), T, cfg)
    assert line.status == "cannot_attest" and line.value is None
    assert "2020-06-15" in line.missing
    assert "not listed" not in line.statement.lower().replace("'not listed'", "")
    assert subs and subs[0].status == "subsequent_event" and subs[0].point_date == date(2020, 6, 15)


def test_listing_fail_null_ipo_never_says_not_listed(cfg):
    rec = base_record()
    rec["revenue"]["public_markets"]["ipo_date"] = None
    line, _, _ = attest(rec, "listing", date(2024, 1, 1), T, cfg)
    assert line.refusal_code == "CANNOT_ATTEST" and "ipo_date" in line.missing
    assert line.value is None


# ---- revenue_band
def test_revenue_band_pass(cfg):
    line, _, ev = attest(base_record(), "revenue_band", date(2024, 2, 1), T, cfg)
    assert line.status == "attested" and line.label == cfg["attest"]["labels"]["revenue_band"]
    assert line.value == {"lower_bound_usd": 1000000, "upper_bound_usd": 5000000}
    assert ev[0].field_path == "revenue.estimated.timeseries[2024-02-01]"


def test_revenue_band_fail_not_yet_recorded(cfg):
    line, _, _ = attest(base_record(), "revenue_band", date(2023, 1, 1), T, cfg)
    assert line.refusal_code == "NOT_YET_RECORDED" and "2024-01-01" in line.missing


def test_revenue_band_fail_null_bounds(cfg, record_for, retrieved_at):
    line, _, _ = attest(record_for("shreebalajigrp.com"), "revenue_band", date(2026, 11, 15), retrieved_at, cfg)
    assert line.status == "cannot_attest" and line.refusal_code == "CANNOT_ATTEST"
    assert "2026-11-10" in line.missing


# ---- domains
def test_domains_pass(cfg):
    line, _, _ = attest(base_record(), "domains", date(2024, 5, 1), T, cfg)
    assert line.status == "attested" and line.value == ["acme.test", "acme-alt.test"]
    assert line.label == cfg["attest"]["labels"]["domains"]
    assert line.point_date == T.date()  # current-only: dated at retrieval, never historical


def test_domains_fail_absent(cfg):
    rec = base_record()
    del rec["basic_info"]["all_domains"]
    line, _, _ = attest(rec, "domains", date(2024, 5, 1), T, cfg)
    assert line.refusal_code == "CANNOT_ATTEST" and "all_domains" in line.missing


# ---- anything else / future / subsequent events
def test_unknown_field(cfg):
    line, _, ev = attest(base_record(), "gstin", date(2024, 1, 1), T, cfg)
    assert line.refusal_code == "NO_RECORD_TYPE" and "gstin" in line.missing and ev == []


@pytest.mark.parametrize("field", ["headcount", "existence", "listing", "revenue_band", "domains"])
def test_future_date(cfg, field):
    line, subs, _ = attest(base_record(), field, date(2024, 6, 2), T, cfg)
    assert line.refusal_code == "FUTURE_DATE" and subs == [] and line.missing
    same_day, _, _ = attest(base_record(), field, T.date(), T, cfg)
    assert same_day.refusal_code != "FUTURE_DATE"


def test_subsequent_events_never_attested(cfg, record_for, retrieved_at):
    line, subs, ev = attest(record_for("delhivery.com"), "headcount", date(2024, 7, 15), retrieved_at, cfg)
    assert subs
    for s in subs:
        assert s.status == "subsequent_event" and s.refusal_code is None
        assert s.point_date > date(2024, 7, 15)
        assert s.evidence_ids and s.evidence_ids[0] not in line.evidence_ids
    ids = [e.id for e in ev]
    assert ids == [f"E{i}" for i in range(1, len(ids) + 1)]  # unique, sequential


def test_evidence_prefix(cfg):
    _, _, ev = attest(base_record(), "headcount", date(2024, 2, 1), T, cfg, evidence_prefix="X")
    assert all(e.id.startswith("X") for e in ev)


def test_statement_uses_config_template(cfg):
    c = copy.deepcopy(cfg)
    c["attest"]["statement_template"] = "P={point_date} V={value} T={retrieved_at}."
    line, _, _ = attest(base_record(), "headcount", date(2024, 2, 1), T, c)
    assert line.statement.startswith("P=2024-02-01 V=employee_count 110 T=2024-06-01T12:00:00+00:00.")
    default, _, _ = attest(base_record(), "headcount", date(2024, 2, 1), T, cfg)
    assert default.statement == ("Data point dated 2024-02-01 states employee_count 110; "
                                 "stored copy retrieved 2024-06-01T12:00:00+00:00.")


def test_labels_read_from_config(cfg):
    c = copy.deepcopy(cfg)
    c["attest"]["labels"]["headcount"] = "estimate"
    line, _, _ = attest(base_record(), "headcount", date(2024, 2, 1), T, c)
    assert line.label == "estimate"


# ---- observe
def test_observe_two_lines_no_ratio(cfg):
    l1, l2 = observe(base_record(), "headcount", date(2024, 1, 1), date(2024, 3, 1), T, cfg)
    assert (l1.value, l2.value) == (100, 120)
    for l in (l1, l2):
        assert l.status == "attested"
        assert "growth" not in l.statement.lower() and "%" not in l.statement


def test_observe_full_unique_evidence(cfg):
    l1, l2, ev = observe_full(base_record(), "headcount", date(2024, 1, 1), date(2024, 3, 1), T, cfg)
    ids = [e.id for e in ev]
    assert len(ids) == len(set(ids)) == 2
    assert l1.evidence_ids != l2.evidence_ids


def test_observe_refuses_independently(cfg):
    l1, l2 = observe(base_record(), "headcount", date(2023, 1, 1), date(2024, 3, 1), T, cfg)
    assert l1.refusal_code == "NOT_YET_RECORDED" and l2.status == "attested"


# ---- council 1519: dated existence, exact template, whole-token ratio match
def test_existence_dated_by_stored_copy(cfg, record_for, retrieved_at):
    line, _, ev = attest(record_for("delhivery.com"), "existence", date(2024, 7, 15), retrieved_at, cfg)
    td = retrieved_at.date()
    assert line.value == 2011 and line.point_date == td and line.label == "as recorded"
    assert ev[0].point_date == td and ev[0].field_path == "basic_info.year_founded"
    assert line.statement == cfg["attest"]["statement_template"].format(
        point_date=td.isoformat(), value="year_founded 2011", retrieved_at=retrieved_at.isoformat(timespec="seconds"))


@pytest.mark.parametrize("field", ["headcount", "existence", "listing", "revenue_band", "domains"])
def test_attested_statement_is_exact_template(cfg, field):
    import re
    line, _, _ = attest(base_record(), field, date(2024, 2, 1), T, cfg)
    assert line.status == "attested"
    pat = re.escape(cfg["attest"]["statement_template"]).replace(r"\{point_date\}", r"\d{4}-\d{2}-\d{2}") \
        .replace(r"\{value\}", ".+").replace(r"\{retrieved_at\}", re.escape(T.isoformat(timespec="seconds")))
    assert re.fullmatch(pat, line.statement), line.statement
