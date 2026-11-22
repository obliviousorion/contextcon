"""Insurer shortlist on regulator figures. Each figure is fetched from its configured regulator page,
located by a pattern, and kept with its quoted passage and char range. A figure that cannot be
fetched or found is CANNOT VERIFY and names what is missing. Never a figure from memory."""
from __future__ import annotations

import re

from .config import load_rules
from .crust import Crust
from .peers import HeldRun
from .rules_engine import rank_insurers


def _figure(c: Crust, spec: dict) -> dict:
    metric = spec["metric"]
    if not spec.get("url"):
        return {"metric": metric, "cannot_verify": True,
                "missing": "no regulator page configured for this figure (rules.yaml insurers.panel)"}
    r = c.web_fetch(spec["url"])
    if r.kind == "held":
        raise HeldRun(r.reason)
    page = (r.data or [{}])[0] if r.ok and isinstance(r.data, list) else {}
    text = page.get("content") or ""
    if not r.ok or not text:
        return {"metric": metric, "cannot_verify": True, "missing": f"regulator page not fetched: {r.reason or 'empty page'}"}
    m = re.search(spec["pattern"], text, re.I | re.S)
    if not m:
        return {"metric": metric, "cannot_verify": True,
                "missing": f"pattern for {metric} not found on {spec['url']} (retrieved {r.retrieved_at})"}
    a, b = max(0, m.start() - 60), min(len(text), m.end() + 60)
    return {"metric": metric, "value": float(m.group("value").replace(",", "")), "period": spec.get("period"),
            "source": {"record": "regulator page via crustdata /web/enrich/live", "url": spec["url"],
                       "passage": text[a:b], "char_range": [a, b], "retrieved_at": r.retrieved_at,
                       "record_date": spec.get("period")}}


def shortlist(c: Crust, as_of: str) -> list[dict]:
    rules = load_rules()["insurers"]
    out = []
    for ins in rules.get("panel", []):
        figs = [_figure(c, {**f, "metric": m}) for m, f in ins["figures"].items()]
        out.append({"insurer": ins["name"], "figures": figs, "reasons": []})
    return rank_insurers(out)
