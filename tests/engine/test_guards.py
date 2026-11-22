"""Malformed input, the wording guard and determinism."""
from __future__ import annotations

import json
from datetime import date, datetime, timezone

import pytest

from backend.engine import FORBIDDEN_PHRASE, attest, audit_claim_full, observe_full
from backend.models import ClaimInput
from tests.engine.conftest import base_record, hidden_cases

T = datetime(2024, 6, 1, 12, 0, tzinfo=timezone.utc)
FIELDS = ["headcount", "existence", "listing", "revenue_band", "domains"]


def _bad_records():
    hc_not_list = base_record(headcount={"timeseries": "oops"})
    bad_date = base_record()
    bad_date["headcount"]["timeseries"][0]["date"] = "not-a-date"
    bad_count = base_record()
    bad_count["headcount"]["timeseries"][1]["employee_count"] = "110"
    no_date = base_record()
    del no_date["revenue"]["estimated"]["timeseries"][0]["date"]
    return {
        "none": None, "empty": {}, "string": "<html>502</html>", "list": [1, 2],
        "error_envelope": {"ok": False, "reason": "timeout"},
        "no_basic_info": {"headcount": {"timeseries": []}},
        "basic_info_not_dict": base_record(basic_info=["x"]),
        "headcount_not_list": hc_not_list, "bad_point_date": bad_date, "bad_count": bad_count,
        "revenue_point_no_date": no_date,
        "revenue_not_dict": base_record(revenue="n/a"),
        "year_founded_str": base_record(basic_info={"year_founded": "2010", "all_domains": ["a.test"]}),
        "domains_not_list": base_record(basic_info={"year_founded": 2010, "all_domains": "a.test"}),
        "ipo_bad": base_record(revenue={"public_markets": {"ipo_date": 20200615}}),
    }


@pytest.mark.parametrize("name", list(_bad_records()))
def test_malformed_never_answers(cfg, name):
    rec = _bad_records()[name]
    relevant = {
        "headcount_not_list": ["headcount"], "bad_point_date": ["headcount"], "bad_count": ["headcount"],
        "revenue_point_no_date": ["revenue_band"], "revenue_not_dict": ["revenue_band", "listing"],
        "year_founded_str": ["existence"], "domains_not_list": ["domains"], "ipo_bad": ["listing"],
    }.get(name, FIELDS)
    for field in relevant:
        line, subs, ev = attest(rec, field, date(2024, 2, 10), T, cfg)
        assert line.status == "cannot_attest", (name, field)
        assert line.refusal_code == "SOURCE_UNAVAILABLE", (name, field, line)
        assert line.value is None and subs == [] and ev == [] and line.missing


def _all_outputs(cfg, retrieved_at, record_for):
    """Every statement / missing / reason the engine produces over a broad sweep."""
    texts = []
    recs = [record_for(d) for d in ("delhivery.com", "tciexpress.in", "shreebalajigrp.com")]
    recs += [base_record(), None, {}]
    dates = [date(1990, 1, 1), date(2011, 6, 1), date(2019, 12, 30), date(2022, 6, 1), date(2024, 7, 15),
             date(2026, 9, 1), date(2026, 10, 15), date(2026, 11, 22), date(2030, 1, 1)]
    for rec in recs:
        for f in FIELDS + ["gstin"]:
            for d in dates:
                line, subs, ev = attest(rec, f, d, retrieved_at, cfg)
                for l in [line, *subs]:
                    texts += [l.statement, l.missing or ""]
                texts += [e.excerpt for e in ev]
            l1, l2, _ = observe_full(rec, f, dates[3], dates[4], retrieved_at, cfg)
            texts += [l1.statement, l2.statement]
        for f in FIELDS + ["headcount_growth", "revenue_growth"]:
            for d in [None, *dates]:
                v, _ = audit_claim_full(rec, ClaimInput(id="k", text="t", field=f, value=100, as_of=d),
                                        retrieved_at, cfg)
                texts += [v.reason, v.line.statement, v.line.missing or ""]
    return texts


def test_wording_never_was_true_on(cfg, retrieved_at, record_for):
    texts = _all_outputs(cfg, retrieved_at, record_for)
    assert len(texts) > 500
    assert not [t for t in texts if FORBIDDEN_PHRASE in t.lower()]


def test_wording_guard_scrubs_hostile_record(cfg):
    rec = base_record()
    rec["basic_info"]["all_domains"] = ["it was true on 2020.test"]
    line, _, _ = attest(rec, "domains", date(2024, 5, 1), T, cfg)
    assert FORBIDDEN_PHRASE not in line.statement.lower()


def test_determinism(cfg, retrieved_at, record_for):
    def run():
        out = []
        for c in hidden_cases().values():
            r = c["request"]
            if r["tool"] != "attest":
                continue
            line, subs, ev = attest(record_for(r["domain"]), r["field"], date.fromisoformat(r["as_of"]),
                                    retrieved_at, cfg)
            out.append(json.dumps([line.model_dump(mode="json"), [s.model_dump(mode="json") for s in subs],
                                   [e.model_dump(mode="json") for e in ev]], sort_keys=True))
        return out
    assert run() == run()


def test_input_record_not_mutated(cfg, record_for, retrieved_at):
    rec = record_for("delhivery.com")
    before = json.dumps(rec, sort_keys=True)
    for f in FIELDS:
        attest(rec, f, date(2024, 7, 15), retrieved_at, cfg)
    assert json.dumps(rec, sort_keys=True) == before
