"""Pure attestation rules (SPEC section 3). No network, no clock, no I/O.

Every public function is deterministic: the same (record, field, dates, config) always gives the
same output. Nothing here reads the current time; `retrieved_at` is always passed in.
"""
from __future__ import annotations

import json
from datetime import date, datetime
from typing import Any, Callable

from backend.models import AttestLine, ClaimInput, ClaimVerdict, Evidence

SOURCE_ENDPOINT = "/company/enrich"
FORBIDDEN_PHRASE = "was true on"
DEFAULT_LABEL = "as recorded"
# Field-name fragments that mark a derived (growth / ratio) claim. Never given a verdict.
_RATIO_TOKENS = ("growth", "ratio", "percent", "pct", "change", "cagr", "multiple", "yoy", "delta", "rate")
# How many points after D are reported as subsequent events: the first and the latest.
_MAX_SUBSEQUENT = 2


class _Malformed(Exception):
    """The record (or the slice of it a rule needs) is not the documented shape."""


# --------------------------------------------------------------------------- helpers

def _as_date(v: Any) -> date:
    if isinstance(v, datetime):
        return v.date()
    if isinstance(v, date):
        return v
    if isinstance(v, str):
        return date.fromisoformat(v.strip()[:10])
    raise TypeError(f"not a date: {v!r}")


def _as_datetime(v: Any) -> datetime:
    if isinstance(v, datetime):
        return v
    if isinstance(v, date):
        return datetime(v.year, v.month, v.day)
    if isinstance(v, str):
        return datetime.fromisoformat(v.strip().replace("Z", "+00:00"))
    raise TypeError(f"not a datetime: {v!r}")


def _point_date(raw: Any) -> date:
    if not isinstance(raw, str):
        raise _Malformed(f"point date is not a string: {raw!r}")
    try:
        return date.fromisoformat(raw.strip()[:10])
    except ValueError as exc:
        raise _Malformed(f"bad point date {raw!r}") from exc


def _fmt_ts(t: datetime) -> str:
    return t.isoformat(timespec="seconds")


def _is_number(v: Any) -> bool:
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def _num(v: Any) -> int | float:
    return int(v) if isinstance(v, float) and v.is_integer() else v


def _excerpt(obj: Any) -> str:
    s = obj if isinstance(obj, str) else json.dumps(obj, sort_keys=True, ensure_ascii=False, default=str)
    return s if len(s) <= 400 else s[:397] + "..."


def _guard(text: str) -> str:
    """Last line of defence for the wording rule: never emit the forbidden phrase."""
    low = text.lower()
    while FORBIDDEN_PHRASE in low:
        i = low.index(FORBIDDEN_PHRASE)
        text = text[:i] + "is stated in a record dated" + text[i + len(FORBIDDEN_PHRASE):]
        low = text.lower()
    return text


def _attest_cfg(config: dict) -> dict:
    a = (config or {}).get("attest") or {}
    return a if isinstance(a, dict) else {}


def _label(config: dict, field: str) -> str:
    labels = _attest_cfg(config).get("labels") or {}
    return labels.get(field, DEFAULT_LABEL) if isinstance(labels, dict) else DEFAULT_LABEL


def _template(config: dict) -> str:
    return _attest_cfg(config).get(
        "statement_template",
        "Data point dated {point_date} states {value}; stored copy retrieved {retrieved_at}.",
    )


def _max_stale(config: dict) -> int:
    return int(_attest_cfg(config).get("max_staleness_days", 14))


def _record_types(config: dict) -> list[str]:
    rt = _attest_cfg(config).get("record_types")
    return list(rt) if isinstance(rt, list) and rt else ["existence", "listing", "headcount", "revenue_band", "domains"]


class _Ctx:
    """Per-call state: evidence numbering and the shared inputs."""

    def __init__(self, field: str, as_of: date, retrieved_at: datetime, config: dict,
                 prefix: str = "E", start: int = 1) -> None:
        self.field = field
        self.as_of = as_of
        self.t = retrieved_at
        self.cfg = config or {}
        self.prefix = prefix
        self.n = start - 1
        self.evidence: list[Evidence] = []

    def ev(self, field_path: str, excerpt: Any, point_date: date | None) -> str:
        self.n += 1
        eid = f"{self.prefix}{self.n}"
        self.evidence.append(Evidence(
            id=eid, kind="company_record", source_endpoint=SOURCE_ENDPOINT, url=None,
            field_path=field_path, excerpt=_excerpt(excerpt), point_date=point_date,
            retrieved_at=self.t, cache_key=None,
        ))
        return eid

    def statement(self, point_date: date | str, value_text: str, suffix: str = "") -> str:
        pd = point_date.isoformat() if isinstance(point_date, date) else point_date
        s = _template(self.cfg).format(point_date=pd, value=value_text, retrieved_at=_fmt_ts(self.t))
        return _guard(s + (" " + suffix if suffix else ""))

    def attested(self, value: Any, point_date: date | None, value_text: str, eids: list[str],
                 label: str | None = None, stmt_date: date | str | None = None, suffix: str = "") -> AttestLine:
        return AttestLine(
            field=self.field, as_of=self.as_of, status="attested", value=value, point_date=point_date,
            label=label or _label(self.cfg, self.field),
            statement=self.statement(stmt_date if stmt_date is not None else point_date, value_text, suffix),
            evidence_ids=eids,
        )

    def subsequent(self, value: Any, point_date: date, value_text: str, eid: str) -> AttestLine:
        return AttestLine(
            field=self.field, as_of=self.as_of, status="subsequent_event", value=value, point_date=point_date,
            label=_label(self.cfg, self.field),
            statement=self.statement(point_date, value_text,
                                     f"Dated after {self.as_of.isoformat()}: reported as a subsequent event, not attested."),
            evidence_ids=[eid],
        )

    def refuse(self, code: str, missing: str, eids: list[str] | None = None,
               point_date: date | None = None, gap_days: int | None = None) -> AttestLine:
        stmt = (f"CANNOT ATTEST {self.field} as of {self.as_of.isoformat()} ({code}): missing {missing.rstrip('.')}. "
                f"Stored copy retrieved {_fmt_ts(self.t)}.")
        return AttestLine(
            field=self.field, as_of=self.as_of, status="cannot_attest", value=None, point_date=point_date,
            label=None, statement=_guard(stmt), refusal_code=code, missing=_guard(missing),
            gap_days=gap_days, evidence_ids=eids or [],
        )


Result = tuple[AttestLine, list[AttestLine]]


# --------------------------------------------------------------------------- record access

def _basic_info(record: dict) -> dict:
    bi = record.get("basic_info")
    if not isinstance(bi, dict):
        raise _Malformed("basic_info is missing or not an object")
    return bi


def _validate_record(record: Any) -> dict:
    if not isinstance(record, dict) or not record:
        raise _Malformed("record is missing or not an object")
    if record.get("ok") is False or "error" in record or "errors" in record:
        raise _Malformed("record is an error envelope")
    _basic_info(record)
    return record


def _section(record: dict, key: str) -> dict | None:
    v = record.get(key)
    if v is None:
        return None
    if not isinstance(v, dict):
        raise _Malformed(f"{key} is not an object")
    return v


def _parse_series(points: Any, path: str) -> list[tuple[date, dict]]:
    if not isinstance(points, list):
        raise _Malformed(f"{path} is not a list")
    out: list[tuple[date, dict]] = []
    for p in points:
        if not isinstance(p, dict) or "date" not in p:
            raise _Malformed(f"{path} has a point without a date")
        out.append((_point_date(p["date"]), p))
    out.sort(key=lambda x: x[0])
    return out


# --------------------------------------------------------------------------- series rule

def _series_rule(ctx: _Ctx, points: Any, path: str, point_value: Callable[[dict], Any],
                 value_text: Callable[[Any], str], value_suffix: str,
                 include_subsequent: bool = True) -> Result:
    """Shared rule for headcount and revenue_band: latest point on/before D, staleness, subsequent events."""
    if points is None:
        return ctx.refuse("CANNOT_ATTEST", f"{path} (absent from the record)"), []
    series = _parse_series(points, path)
    if not series:
        return ctx.refuse("CANNOT_ATTEST", f"{path} (the series has no data points)"), []

    D = ctx.as_of
    before = [(d, p) for d, p in series if d <= D]
    after = [(d, p) for d, p in series if d > D]

    def _main() -> AttestLine:
        if not before:
            first_d, first_p = series[0]
            eid = ctx.ev(f"{path}[{first_d.isoformat()}]{value_suffix}", first_p, first_d)
            return ctx.refuse(
                "NOT_YET_RECORDED",
                f"a {path} point dated on or before {D.isoformat()}; the first point is dated {first_d.isoformat()}",
                [eid],
            )

        d, p = before[-1]
        eid = ctx.ev(f"{path}[{d.isoformat()}]{value_suffix}", p, d)
        v = point_value(p)
        if v is None:
            return ctx.refuse(
                "CANNOT_ATTEST",
                f"a value at {path}[{d.isoformat()}]{value_suffix} (the latest point on or before "
                f"{D.isoformat()} is dated {d.isoformat()} and its value is null)",
                [eid], point_date=d,
            )

        gap = (D - d).days
        max_stale = _max_stale(ctx.cfg)
        if gap > max_stale:
            return ctx.refuse(
                "STALE_DATA",
                f"a {path} point within {max_stale} days before {D.isoformat()}; the nearest point on or before "
                f"{D.isoformat()} is dated {d.isoformat()}, {gap} days earlier",
                [eid], point_date=d, gap_days=gap,
            )

        return ctx.attested(v, d, value_text(v), [eid])

    line = _main()  # the attested / refused point gets the first evidence id
    subsequent: list[AttestLine] = []
    if include_subsequent:
        valued_after = [(d, p, point_value(p)) for d, p in after]
        valued_after = [x for x in valued_after if x[2] is not None]
        picks = valued_after[:1] + (valued_after[-1:] if len(valued_after) > 1 else [])
        for d, p, v in picks:
            eid = ctx.ev(f"{path}[{d.isoformat()}]{value_suffix}", p, d)
            subsequent.append(ctx.subsequent(v, d, value_text(v), eid))
    return line, subsequent


def _headcount_value(p: dict) -> Any:
    v = p.get("employee_count")
    if v is None:
        return None
    if not _is_number(v):
        raise _Malformed(f"employee_count is not a number: {v!r}")
    return _num(v)


def _revenue_value(p: dict) -> Any:
    lo, hi = p.get("revenue_lower_bound_usd"), p.get("revenue_upper_bound_usd")
    if lo is None or hi is None:
        return None
    if not (_is_number(lo) and _is_number(hi)):
        raise _Malformed("revenue bounds are not numbers")
    return {"lower_bound_usd": _num(lo), "upper_bound_usd": _num(hi)}


def _rule_headcount(ctx: _Ctx, record: dict, include_subsequent: bool = True) -> Result:
    hc = _section(record, "headcount")
    points = None if hc is None else hc.get("timeseries")
    return _series_rule(ctx, points, "headcount.timeseries", _headcount_value,
                        lambda v: f"employee_count {v}", ".employee_count", include_subsequent)


def _rule_revenue_band(ctx: _Ctx, record: dict, include_subsequent: bool = True) -> Result:
    rev = _section(record, "revenue")
    est = None if rev is None else rev.get("estimated")
    if est is not None and not isinstance(est, dict):
        raise _Malformed("revenue.estimated is not an object")
    points = None if est is None else est.get("timeseries")
    return _series_rule(
        ctx, points, "revenue.estimated.timeseries", _revenue_value,
        lambda v: f"estimated revenue between USD {v['lower_bound_usd']:,} and USD {v['upper_bound_usd']:,}",
        "", include_subsequent)


def _rule_existence(ctx: _Ctx, record: dict, include_subsequent: bool = True) -> Result:
    yf = _basic_info(record).get("year_founded")
    if yf is None:
        return ctx.refuse("CANNOT_ATTEST", "year_founded (basic_info.year_founded is null in the record)"), []
    if not (isinstance(yf, int) and not isinstance(yf, bool)):
        raise _Malformed(f"year_founded is not an integer: {yf!r}")
    eid = ctx.ev("basic_info.year_founded", {"year_founded": yf}, None)
    if ctx.as_of.year < yf:
        return ctx.refuse(
            "BEFORE_FOUNDING",
            f"any record of the company in {ctx.as_of.year}; the record's founding year is {yf}",
            [eid],
        ), []
    return ctx.attested(yf, None, f"year_founded {yf}", [eid],
                        stmt_date="n/a (undated record field basic_info.year_founded)"), []


def _rule_listing(ctx: _Ctx, record: dict, include_subsequent: bool = True) -> Result:
    rev = _section(record, "revenue")
    pm = None if rev is None else rev.get("public_markets")
    if pm is not None and not isinstance(pm, dict):
        raise _Malformed("revenue.public_markets is not an object")
    ipo_raw = None if pm is None else pm.get("ipo_date")
    if ipo_raw is None:
        return ctx.refuse(
            "CANNOT_ATTEST",
            "revenue.public_markets.ipo_date (null in the record; no listing record to attest, "
            "and an absent IPO date is not read as 'not listed')",
        ), []
    ipo = _point_date(ipo_raw)
    excerpt = {"ipo_date": ipo_raw, "stock_symbols": pm.get("stock_symbols")}
    eid = ctx.ev("revenue.public_markets.ipo_date", excerpt, ipo)
    symbols = pm.get("stock_symbols") if isinstance(pm.get("stock_symbols"), list) else []
    sym_txt = f" (symbols: {', '.join(map(str, symbols))})" if symbols else ""
    text = f"IPO date {ipo.isoformat()}{sym_txt}"
    if ipo > ctx.as_of:
        subs = [ctx.subsequent("listed", ipo, text, eid)] if include_subsequent else []
        return ctx.refuse(
            "NOT_YET_RECORDED",
            f"a listing record dated on or before {ctx.as_of.isoformat()}; the record's IPO date "
            f"{ipo.isoformat()} is after it (this is not a finding of 'not listed')",
            [eid],
        ), subs
    return ctx.attested("listed", ipo, text, [eid], label=DEFAULT_LABEL), []


def _rule_domains(ctx: _Ctx, record: dict, include_subsequent: bool = True) -> Result:
    doms = _basic_info(record).get("all_domains")
    if doms is None:
        return ctx.refuse("CANNOT_ATTEST", "basic_info.all_domains (absent from the record)"), []
    if not isinstance(doms, list) or not all(isinstance(x, str) for x in doms):
        raise _Malformed("all_domains is not a list of strings")
    if not doms:
        return ctx.refuse("CANNOT_ATTEST", "basic_info.all_domains (empty in the record)"), []
    td = ctx.t.date()
    eid = ctx.ev("basic_info.all_domains", doms, td)
    return ctx.attested(
        list(doms), td, f"all_domains {', '.join(doms)}", [eid],
        suffix="True at retrieval only; this is not a historical record of the domains.",
    ), []


_RULES = {
    "headcount": _rule_headcount,
    "existence": _rule_existence,
    "listing": _rule_listing,
    "revenue_band": _rule_revenue_band,
    "domains": _rule_domains,
}


# --------------------------------------------------------------------------- public: attest / observe

def _attest_ctx(record: Any, field: str, as_of: Any, retrieved_at: Any, config: dict,
                prefix: str, start: int, include_subsequent: bool) -> tuple[AttestLine, list[AttestLine], _Ctx]:
    D = _as_date(as_of)
    T = _as_datetime(retrieved_at)
    fld = field if isinstance(field, str) else str(field)
    ctx = _Ctx(fld, D, T, config, prefix, start)

    if fld not in _RULES or fld not in _record_types(config):
        return ctx.refuse(
            "NO_RECORD_TYPE",
            f"a record type for '{fld}'; AsOf attests only: {', '.join(_record_types(config))}",
        ), [], ctx
    if D > T.date():
        return ctx.refuse(
            "FUTURE_DATE",
            f"a record retrieved on or after {D.isoformat()}; the stored copy was retrieved "
            f"{_fmt_ts(T)}, before the requested date",
        ), [], ctx
    try:
        rec = _validate_record(record)
        line, subs = _RULES[fld](ctx, rec, include_subsequent)
    except (_Malformed, TypeError, ValueError, KeyError, AttributeError) as exc:
        ctx.evidence.clear()
        ctx.n = start - 1
        return ctx.refuse("SOURCE_UNAVAILABLE",
                          f"a well-formed company record from {SOURCE_ENDPOINT} ({exc})"), [], ctx
    return line, subs, ctx


def attest(record: dict | None, field: str, as_of: date, retrieved_at: datetime, config: dict,
           evidence_prefix: str = "E") -> tuple[AttestLine, list[AttestLine], list[Evidence]]:
    """Attest one field of a company record as of D. Returns (line, subsequent_events, evidence).

    Evidence ids are f"{evidence_prefix}{n}" from 1, unique within the call."""
    line, subs, ctx = _attest_ctx(record, field, as_of, retrieved_at, config, evidence_prefix, 1, True)
    return line, subs, list(ctx.evidence)


def observe_full(record: dict | None, field: str, d1: date, d2: date, retrieved_at: datetime, config: dict,
                 evidence_prefix: str = "E") -> tuple[AttestLine, AttestLine, list[Evidence]]:
    """Two independent attestations side by side, with their evidence. Never a growth or ratio value."""
    l1, _, c1 = _attest_ctx(record, field, d1, retrieved_at, config, evidence_prefix, 1, False)
    l2, _, c2 = _attest_ctx(record, field, d2, retrieved_at, config, evidence_prefix, c1.n + 1, False)
    return l1, l2, list(c1.evidence) + list(c2.evidence)


def observe(record: dict | None, field: str, d1: date, d2: date, retrieved_at: datetime,
            config: dict) -> tuple[AttestLine, AttestLine]:
    """Two dated AttestLines side by side. Never a growth or ratio value."""
    l1, l2, _ = observe_full(record, field, d1, d2, retrieved_at, config)
    return l1, l2


# --------------------------------------------------------------------------- public: audit

def is_ratio_field(field: str) -> bool:
    f = (field or "").lower()
    return any(tok in f for tok in _RATIO_TOKENS)


def _base_field(field: str) -> str | None:
    f = (field or "").lower()
    if f.startswith("headcount") or f.startswith("employee"):
        return "headcount"
    if f.startswith("revenue"):
        return "revenue_band"
    return None


def _audit_cfg(config: dict) -> dict:
    a = (config or {}).get("audit") or {}
    return a if isinstance(a, dict) else {}


def _cite(ids: list[str]) -> str:
    return "[" + ", ".join(ids) + "]" if ids else "[no evidence]"


def _verdict(claim: ClaimInput, verdict: str, line: AttestLine, why: str) -> ClaimVerdict:
    dated = f"dated {claim.as_of.isoformat()}" if claim.as_of else "undated"
    reason = (f"{verdict}: claim {claim.id} ('{claim.text}'; {claim.field} = {claim.value!r}, {dated}). {why} Record {_cite(line.evidence_ids)}: "
              f"{line.statement}")
    return ClaimVerdict(claim_id=claim.id, verdict=verdict, line=line, reason=_guard(reason))


def _ratio_audit(record: Any, claim: ClaimInput, retrieved_at: datetime, config: dict,
                 prefix: str) -> tuple[ClaimVerdict, list[Evidence]]:
    T = _as_datetime(retrieved_at)
    end = min(claim.as_of, T.date()) if claim.as_of else T.date()
    ctx = _Ctx(claim.field, end, T, config, prefix, 1)
    base = _base_field(claim.field)
    rule_txt = ("AsOf never derives a growth or ratio verdict from two lower-bound counts; "
                "the dated values are shown side by side instead.")
    missing = f"a dated '{claim.field}' record; {rule_txt}"
    try:
        rec = _validate_record(record)
        if base == "headcount":
            hc = _section(rec, "headcount")
            pts, path, vf, suffix = (None if hc is None else hc.get("timeseries")), "headcount.timeseries", \
                _headcount_value, ".employee_count"
            txt = lambda v: f"employee_count {v}"  # noqa: E731
        elif base == "revenue_band":
            r = _section(rec, "revenue")
            est = None if r is None else r.get("estimated")
            pts = est.get("timeseries") if isinstance(est, dict) else None
            path, vf, suffix = "revenue.estimated.timeseries", _revenue_value, ""
            txt = lambda v: f"estimated revenue between USD {v['lower_bound_usd']:,} and USD {v['upper_bound_usd']:,}"  # noqa: E731
        else:
            pts = None
        valued = []
        if pts is not None:
            valued = [(d, p, vf(p)) for d, p in _parse_series(pts, path) if d <= end]
            valued = [x for x in valued if x[2] is not None]
    except (_Malformed, TypeError, ValueError, KeyError, AttributeError) as exc:
        ctx.evidence.clear()
        line = ctx.refuse("SOURCE_UNAVAILABLE", f"a well-formed company record from {SOURCE_ENDPOINT} ({exc})")
        return _verdict(claim, "cannot_verify", line, "The source record is unavailable or malformed."), []

    if not valued:
        line = ctx.refuse("NO_RECORD_TYPE", missing)
        return _verdict(claim, "cannot_verify", line,
                        f"Growth or ratio claim; no dated values to show. {rule_txt}"), list(ctx.evidence)

    picks = [valued[0]] + ([valued[-1]] if len(valued) > 1 else [])
    ids, parts = [], []
    for d, p, v in picks:
        eid = ctx.ev(f"{path}[{d.isoformat()}]{suffix}", p, d)
        ids.append(eid)
        parts.append(f"[{eid}] " + ctx.statement(d, txt(v)))
    line = ctx.refuse("NO_RECORD_TYPE", missing, ids)
    line = line.model_copy(update={"statement": _guard(line.statement + " Side by side: " + " ".join(parts))})
    why = "Growth or ratio claim: no verdict is derived."
    return _verdict(claim, "cannot_verify", line, why), list(ctx.evidence)


def _claim_number(v: Any) -> float | None:
    if _is_number(v):
        return float(v)
    if isinstance(v, str):
        try:
            return float(v.replace(",", "").strip())
        except ValueError:
            return None
    return None


_LISTED = {"listed", "true", "yes", "public"}
_NOT_LISTED = {"not listed", "unlisted", "false", "no", "private"}


def _compare(claim: ClaimInput, line: AttestLine, config: dict) -> tuple[str, str]:
    acfg = _audit_cfg(config)
    window = int(acfg.get("contradict_date_window_days", 14))
    tol = float(acfg.get("contradict_tolerance_pct", 25))
    f = claim.field
    cv = claim.value

    if f in ("headcount", "revenue_band", "domains"):
        gap = abs((claim.as_of - line.point_date).days) if line.point_date else None
        if gap is None or gap > window:
            return "cannot_verify", (f"The claim's date is not within {window} days of the attested point "
                                     f"dated {line.point_date}.")

    if f == "headcount":
        c = _claim_number(cv)
        if c is None:
            return "cannot_verify", "The claimed value is not a number."
        v = float(line.value)
        pct = abs(c - v) / v * 100 if v else (0.0 if c == 0 else float("inf"))
        if pct > tol:
            return "contradict", f"The claimed {c:g} differs from the recorded {v:g} by {pct:.1f}%, over the {tol:g}% tolerance."
        return "agree", f"The claimed {c:g} is within {tol:g}% of the recorded {v:g} ({pct:.1f}%)."

    if f == "revenue_band":
        c = _claim_number(cv)
        if c is None:
            return "cannot_verify", "The claimed value is not a number in USD."
        lo, hi = float(line.value["lower_bound_usd"]), float(line.value["upper_bound_usd"])
        if lo <= c <= hi:
            return "agree", f"The claimed USD {c:,.0f} lies within the estimated band."
        bound = lo if c < lo else hi
        pct = abs(c - bound) / bound * 100 if bound else float("inf")
        if pct > tol:
            return "contradict", f"The claimed USD {c:,.0f} lies {pct:.1f}% outside the estimated band, over the {tol:g}% tolerance."
        return "cannot_verify", f"The claimed USD {c:,.0f} lies just outside the estimated band ({pct:.1f}%), within tolerance."

    if f == "domains":
        claimed = [cv] if isinstance(cv, str) else (list(cv) if isinstance(cv, (list, tuple)) else None)
        if not claimed or not all(isinstance(x, str) for x in claimed):
            return "cannot_verify", "The claimed value is not a domain or list of domains."
        have = {d.lower() for d in line.value}
        if all(x.lower().strip() in have for x in claimed):
            return "agree", "Every claimed domain is in the record's domains at retrieval."
        return "cannot_verify", "A claimed domain is not in the record; absence is not read as a negative finding."

    if f == "listing":
        key = str(cv).strip().lower() if cv is not None else ""
        if cv is True or key in _LISTED:
            return "agree", "The record has an IPO date on or before the claim's date."
        if cv is False or key in _NOT_LISTED:
            return "contradict", "The record has an IPO date on or before the claim's date."
        return "cannot_verify", "The claimed value is not 'listed' or 'not listed'."

    if f == "existence":
        if cv is True:
            return "agree", "The record's founding year is on or before the claim's date."
        if cv is False:
            return "contradict", "The record's founding year is on or before the claim's date."
        c = _claim_number(cv)
        if c is None or not c.is_integer():
            return "cannot_verify", "The claimed value is not a founding year."
        if int(c) == line.value:
            return "agree", "The claimed founding year matches the record."
        return "contradict", f"The claimed founding year {int(c)} differs from the record's {line.value}."

    return "cannot_verify", "No comparison rule for this field."


def audit_claim_full(record: dict | None, claim: ClaimInput, retrieved_at: datetime, config: dict,
                     evidence_prefix: str = "E") -> tuple[ClaimVerdict, list[Evidence]]:
    """Grade one structured claim. Returns (verdict, evidence)."""
    if is_ratio_field(claim.field):
        return _ratio_audit(record, claim, retrieved_at, config, evidence_prefix)

    T = _as_datetime(retrieved_at)
    if claim.as_of is None:
        line, _, ev = attest(record, claim.field, T.date(), T, config, evidence_prefix)
        return _verdict(claim, "cannot_verify", line,
                        "The claim carries no date; agree or contradict needs a dated claim near an attested point."), ev
    line, _, ev = attest(record, claim.field, claim.as_of, T, config, evidence_prefix)
    if line.status != "attested":
        return _verdict(claim, "cannot_verify", line,
                        f"The record cannot attest {claim.field} as of {claim.as_of.isoformat()} ({line.refusal_code})."), ev
    if claim.value is None:
        return _verdict(claim, "cannot_verify", line, "The claim carries no value to compare."), ev
    verdict, why = _compare(claim, line, config)
    return _verdict(claim, verdict, line, why), ev


def audit_claim(record: dict | None, claim: ClaimInput, retrieved_at: datetime, config: dict) -> ClaimVerdict:
    """Grade one structured claim agree / contradict / cannot_verify (SPEC section 3 audit rules)."""
    return audit_claim_full(record, claim, retrieved_at, config)[0]


def retrieved_at_from_envelope(envelope: Any) -> datetime | None:
    """The retrieval timestamp of a fixture / cache envelope, if it carries one."""
    if isinstance(envelope, dict):
        for k in ("retrieved_at", "ts"):
            v = envelope.get(k)
            if isinstance(v, str):
                try:
                    return _as_datetime(v)
                except ValueError:
                    return None
    return None
