"""Required config keys are indexed with no fallback; a missing key raises an error naming it."""
from __future__ import annotations

import copy
from datetime import date, datetime, timezone

import pytest

from backend.engine import attest, audit_claim
from backend.engine.config import ConfigKeyError, require
from backend.models import ClaimInput
from tests.engine.conftest import base_record

T = datetime(2024, 6, 1, 12, 0, tzinfo=timezone.utc)

ATTEST_KEYS = ["attest.max_staleness_days", "attest.labels", "attest.statement_template"]
AUDIT_KEYS = ["audit.contradict_date_window_days", "audit.contradict_tolerance_pct"]


def _without(cfg: dict, dotted: str) -> dict:
    c = copy.deepcopy(cfg)
    sec, key = dotted.split(".")
    del c[sec][key]
    return c


def test_require_names_key(cfg):
    assert require(cfg, "attest.max_staleness_days") == cfg["attest"]["max_staleness_days"]
    with pytest.raises(ConfigKeyError, match=r"attest\.nope"):
        require(cfg, "attest.nope")
    with pytest.raises(ConfigKeyError, match=r"audit\.contradict_tolerance_pct"):
        require({}, "audit.contradict_tolerance_pct")


@pytest.mark.parametrize("dotted", ATTEST_KEYS)
def test_attest_missing_key_raises(cfg, dotted):
    with pytest.raises(ConfigKeyError, match=dotted.replace(".", r"\.")):
        attest(base_record(), "headcount", date(2024, 3, 5), T, _without(cfg, dotted))


@pytest.mark.parametrize("dotted", AUDIT_KEYS)
def test_audit_missing_key_raises(cfg, dotted):
    claim = ClaimInput(id="K1", text="headcount 120", field="headcount", value=120, as_of=date(2024, 3, 1))
    with pytest.raises(ConfigKeyError, match=dotted.replace(".", r"\.")):
        audit_claim(base_record(), claim, T, _without(cfg, dotted))


def test_full_config_still_works(cfg):
    line, _, _ = attest(base_record(), "headcount", date(2024, 3, 5), T, cfg)
    assert line.status == "attested"
