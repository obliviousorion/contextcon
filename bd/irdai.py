"""Regulator figures from IRDAI's own PDF, extracted by code (never typed in).

`bd irdai-extract <pdf> --url <address>` reads the Annual Report, finds Statement 10 ("Incurred claims ratio of
general and health insurers"), and stores each standalone health insurer's row with the PDF address, page number
and the quoted row. Only exact (normalised) name matches are attached to an insurer; anything else stays
CANNOT VERIFY. Incurred claims ratio = claims incurred / premium earned. It is NOT a claim settlement ratio.
"""
from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path

from .store import ROOT

OUT = ROOT / "fixtures" / "irdai" / "statement10_health_icr.json"
TITLE = "INCURRED CLAIMS RATIO OF GENERAL AND HEALTH INSURERS"
METRIC = "Incurred claims ratio, health (%)"
MEANING = ("claims incurred as a share of premium earned, from the regulator's table. It is not the share of claims "
           "that were paid, and a higher number is not simply better or worse.")


def norm(name: str) -> str:
    n = name.lower().replace("&", "and")
    n = re.sub(r"\bcompany\b", "co", n)
    n = re.sub(r"\blimited\b", "ltd", n)
    n = re.sub(r"[^a-z0-9 ]", " ", n)
    return re.sub(r"\s+", " ", n).strip()


def extract(pdf_path: str, pdf_url: str) -> dict:
    from pypdf import PdfReader
    rd = PdfReader(pdf_path)
    for i, pg in enumerate(rd.pages):
        text = pg.extract_text() or ""
        if TITLE not in text or "STANDALONE HEALTH INSURERS" not in text:
            continue
        section = text.split("STANDALONE HEALTH INSURERS", 1)[1]
        rows = []
        for line in section.splitlines():
            line = line.strip()
            if not line or line.startswith(("Standalone Health Insurers' Total", "GRAND TOTAL", "Note")):
                if line.startswith(("GRAND TOTAL", "Note")):
                    break
                continue
            m = re.match(r"^(?P<name>.+?(?:Ltd|Limited)\.?)\s+(?P<rest>(?:\S+\s*){12})$", line)
            if not m:
                continue
            vals = m.group("rest").split()
            # columns: Fire, Marine, Motor, Health, Others, Total; each 2023-24 then 2024-25 -> Health = 6, 7
            rows.append({"insurer": m.group("name"), "quoted_row": line, "health_2023_24": vals[6], "health_2024_25": vals[7]})
        return {"source": {"document": "IRDAI Annual Report 2024-25", "url": pdf_url, "page": i + 1,
                           "statement": "Statement 10", "table": TITLE.title(), "section": "Standalone Health Insurers",
                           "columns": "Health 2023-24, Health 2024-25", "extracted_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                           "extractor": "pypdf text extraction, bd/irdai.py"}, "rows": rows}
    raise ValueError("Statement 10 not found in this PDF")


def save(data: dict) -> Path:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(data, indent=1))
    return OUT


def load() -> dict | None:
    return json.loads(OUT.read_text()) if OUT.exists() else None


def figures_for(company_name: str) -> list[dict] | None:
    """-> figures with quoted row, or None if no exact normalised match (caller shows CANNOT VERIFY)."""
    data = load()
    if not data:
        return None
    row = next((r for r in data["rows"] if norm(r["insurer"]) == norm(company_name)), None)
    if not row:
        return None
    out = []
    for col, fy in (("health_2024_25", "FY 2024-25"), ("health_2023_24", "FY 2023-24")):
        v = row[col]
        if not re.fullmatch(r"-?\d+(\.\d+)?", v) or v not in row["quoted_row"]:
            continue  # "-", "NA" or not in the quoted row: not a figure
        s = data["source"]
        out.append({"label": f"{METRIC}, {fy}", "value": f"{v}%", "meaning": MEANING,
                    "source": {"record": f"{s['document']}, {s['statement']}", "url": s["url"],
                               "field_path": f"page {s['page']}, {s['section']}, Health {fy[3:]}",
                               "passage": row["quoted_row"], "record_date": "2025-03-31", "retrieved_at": s["extracted_at"]}})
    return out or None
