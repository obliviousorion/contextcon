"""Authorize the INR exposure of a USD payable using dated ECB reference rates."""

import json
from datetime import date, timedelta
from decimal import Decimal, DecimalException, ROUND_HALF_UP
from http.client import HTTPException
from urllib.error import URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


ENDPOINT = "https://api.frankfurter.dev/v2/providers/ecb/rates"
TIMEOUT_SECONDS = 5
MAX_BODY = 32_768


def _parse_date(value):
    try:
        day = date.fromisoformat(value)
    except (ValueError, TypeError) as exc:
        raise ValueError("Expected an invoice or rate date in YYYY-MM-DD format.") from exc
    if day.isoformat() != value:
        raise ValueError("Expected a calendar date in YYYY-MM-DD format.")
    return day


def _live_quote(day):
    start = day - timedelta(days=7)
    query = urlencode({"from": start.isoformat(), "to": day.isoformat(),
                       "base": "USD", "quotes": "INR"})
    url = f"{ENDPOINT}?{query}"
    request = Request(url, headers={"Accept": "application/json", "User-Agent": "FreightClose/1.0"})
    try:
        with urlopen(request, timeout=TIMEOUT_SECONDS) as response:
            body = response.read(MAX_BODY + 1)
        if len(body) > MAX_BODY:
            raise ValueError("FX response exceeded the size limit.")
        observations = json.loads(body, parse_float=Decimal)
        if not isinstance(observations, list):
            raise ValueError("FX response has no observation list.")
        rates = {}
        for row in observations:
            if row["base"] != "USD" or row["quote"] != "INR":
                raise ValueError("FX response contains an unexpected currency pair.")
            observed = _parse_date(row["date"])
            rate = Decimal(str(row["rate"]))
            if not rate.is_finite() or rate <= 0 or rate > 1_000_000:
                raise ValueError("Invalid reference rate.")
            if start <= observed <= day:
                if observed in rates and rates[observed] != rate:
                    raise ValueError("Conflicting FX observations.")
                rates[observed] = rate
        if not rates:
            raise ValueError("No USD/INR observation inside the permitted seven-day window.")
        latest = max(rates)
        return latest, rates[latest], url
    except (URLError, OSError, HTTPException, TypeError, KeyError, DecimalException, ValueError) as exc:
        raise ValueError(f"Cannot verify the USD/INR rate for {day}. Source: {url}. {exc}") from exc


def assess(payable_cents: int, invoice_date: str, cap_paise: int, mode: str) -> dict:
    for amount in (payable_cents, cap_paise):
        if type(amount) is not int or not 0 <= amount <= 10**16:
            raise ValueError("The payable and INR authority cap must be nonnegative minor-unit integers.")
    day = _parse_date(invoice_date)
    if not date(1999, 1, 1) <= day <= date.today():
        raise ValueError("Invoice date must be between 1999-01-01 and today.")
    if mode == "live":
        observed, rate, url = _live_quote(day)
        source = f"Frankfurter / ECB [{observed}, USD/INR rate = {rate}]"
    elif mode == "mock":
        observed, rate, url = day, Decimal("85.00"), ""
        source = f"Test fixture FX-85 [{day}, USD/INR rate = 85.00]"
    else:
        raise ValueError("FX mode must be live or mock.")
    paise = int((Decimal(payable_cents) * rate).quantize(Decimal("1"), rounding=ROUND_HALF_UP))
    approved = paise <= cap_paise
    comparison = "within" if approved else "above"
    reason = (f"USD {Decimal(payable_cents)/100:,.2f} × {rate} = INR {Decimal(paise)/100:,.2f}, "
              f"{comparison} the INR {Decimal(cap_paise)/100:,.2f} authorization cap. "
              f"Reference rate dated {observed}.")
    sources = [source, f"Authorization policy: cap_paise = {cap_paise}"]
    if url:
        sources.append(url)
    return {"approved": approved, "reason": reason, "sources": sources, "rate": str(rate),
            "rate_date": observed.isoformat(), "payable_paise": paise, "url": url}
