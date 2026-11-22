"""Regenerate the UI fixtures from real CLI output in replay mode (0 credits, no network).

Run from AsOf/:  uv run python frontend/fixtures/regen_fixtures.py
Every case file below is the exact JSON the CLI prints; only the UI's labels and descriptions are kept.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

ASOF = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent


def cli(*args: str) -> dict:
    env = dict(os.environ, MODE="replay", ASOF_TODAY="2026-11-22", ASOF_STATE_DIR=STATE, PYTHONPATH=str(ASOF))
    env.pop("CRUST_KEY", None)  # replay never needs the key
    out = subprocess.run([sys.executable, "-m", "backend.cli", *args], cwd=ASOF, env=env,
                         capture_output=True, text=True, check=True).stdout
    d = json.loads(out)
    if isinstance(d.get("cost"), dict) and "cost_note" in d:  # the CostPanel reads cost.cost_note
        d["cost"]["cost_note"] = d["cost_note"]
    return d


def line(cf: dict, field: str) -> dict:
    return next(l for l in cf["attestation"]["lines"] if l["field"] == field)


STATE = tempfile.mkdtemp(prefix="asof-ui-fixtures-")

refusals = json.loads((OUT / "demo_refusals.json").read_text())

for key, dom, d in (("C02", "delhivery.com", "2022-06-01"), ("C07", "tciexpress.in", "2026-10-15")):
    cf = cli("dispute", dom, d)
    refusals["cases"][key]["case_file"] = cf
    refusals["cases"][key]["line"] = line(cf, "headcount")
refusals["cases"]["C08"]["resolve"] = cli("resolve", "--name", "Shree Balaji Logistics")

for t in refusals["timeline"]:
    cf = cli("clear", t["domain"]) if t["tool"] == "clear" else cli("dispute", t["domain"], t["date"])
    t["case_file"] = cf

(OUT / "demo_refusals.json").write_text(json.dumps(refusals, indent=2, ensure_ascii=False) + "\n")
(OUT / "demo_casefile.json").write_text(json.dumps(cli("clear", "delhivery.com"), indent=2, ensure_ascii=False) + "\n")
print("regenerated demo_refusals.json and demo_casefile.json from CLI output; state in", STATE)
