"""Shared fixtures for engine tests: the recorded enrich records, keyed by domain."""
from __future__ import annotations

import copy
import json
from datetime import datetime
from pathlib import Path

import pytest

from backend.engine import load_config, retrieved_at_from_envelope

ROOT = Path(__file__).resolve().parents[2]
ENRICH = ROOT / "fixtures" / "live_check" / "enrich.json"
CASES = ROOT / "tests" / "cases" / "hidden_test_cases.json"


def _load_enrich():
    env = json.loads(ENRICH.read_text())
    by_domain: dict[str, dict] = {}
    for item in env["data"]:
        rec = item["matches"][0]["company_data"]
        bi = rec["basic_info"]
        for d in [bi.get("primary_domain"), *(bi.get("all_domains") or [])]:
            if d:
                by_domain.setdefault(d, rec)
    return by_domain, retrieved_at_from_envelope(env)


_BY_DOMAIN, _RETRIEVED_AT = _load_enrich()


@pytest.fixture(scope="session")
def cfg() -> dict:
    return load_config(ROOT / "config.yaml")


@pytest.fixture(scope="session")
def retrieved_at() -> datetime:
    assert _RETRIEVED_AT is not None
    return _RETRIEVED_AT


@pytest.fixture
def record_for():
    """record_for(domain) -> a deep copy of that company's company_data."""
    def _get(domain: str) -> dict:
        return copy.deepcopy(_BY_DOMAIN[domain])
    return _get


def hidden_cases() -> dict[str, dict]:
    return {c["id"]: c for c in json.loads(CASES.read_text())["cases"]}


def base_record(**over) -> dict:
    """A minimal synthetic company_data record for field-rule tests."""
    rec = {
        "crustdata_company_id": 1,
        "basic_info": {"name": "Acme", "primary_domain": "acme.test", "year_founded": 2010,
                       "all_domains": ["acme.test", "acme-alt.test"]},
        "headcount": {"timeseries": [
            {"date": "2024-01-01", "employee_count": 100},
            {"date": "2024-02-01", "employee_count": 110},
            {"date": "2024-03-01", "employee_count": 120},
        ]},
        "revenue": {
            "estimated": {"timeseries": [
                {"date": "2024-01-01", "revenue_lower_bound_usd": 1000000, "revenue_upper_bound_usd": 5000000},
                {"date": "2024-02-01", "revenue_lower_bound_usd": 1000000, "revenue_upper_bound_usd": 5000000},
            ]},
            "public_markets": {"ipo_date": "2020-06-15", "stock_symbols": ["ACME"], "fiscal_year_end": None},
        },
    }
    rec.update(over)
    return rec
