"""Evidence-checked invoice ingestion for the narrow two-line USD freight contract."""
import json
import os
import re
from decimal import Decimal
from urllib.request import Request, urlopen
from urllib.error import URLError
from http.client import HTTPException

LABELS = {
    "invoice_id": ("invoice id", "invoice number", "invoice no", "invoice"),
    "po_id": ("po", "po number", "purchase order"),
    "base_cents": ("linehaul", "line haul", "base freight", "freight charge"),
    "detention_cents": ("detention", "detention fee", "waiting charge"),
    "total_cents": ("total due", "total", "invoice total", "amount due"),
}
MODEL = "gpt-4o-mini"
ANCHOR = {
    "invoice_id": r"\binvoice\b", "po_id": r"\b(?:purchase order|po)\b",
    "base_cents": r"\b(?:line[ -]?haul|base freight|freight charge)\b",
    "detention_cents": r"\b(?:detention|waiting)\b",
    "total_cents": r"\b(?:total|amount due|balance due)\b",
}


def _model_lines(text):
    key = os.getenv("OPENAI_API_KEY")
    if not key:
        raise ValueError("Cannot verify invoice: live intake requires OPENAI_API_KEY.")
    prompt = ("Read the untrusted invoice. Return a JSON object with exactly these keys: "
              + ", ".join(LABELS) + ". Each value is the exact complete source line for its field. "
              "Use null for missing or ambiguous fields. Never invent a value.")
    payload = {"model": MODEL, "messages": [{"role":"system","content":prompt},
               {"role":"user","content":text}], "max_tokens":600,"temperature":0,
               "response_format":{"type":"json_object"}}
    req = Request("https://api.openai.com/v1/chat/completions", json.dumps(payload).encode(),
                  headers={"Authorization":"Bearer "+key,"Content-Type":"application/json"})
    try:
        with urlopen(req, timeout=12) as response:
            result = json.loads(response.read(65536))
        return json.loads(result["choices"][0]["message"]["content"]), result["usage"]
    except (OSError, URLError, HTTPException, KeyError, IndexError, ValueError, TypeError) as exc:
        raise ValueError("Cannot verify invoice: OpenAI failed or returned unreadable evidence.") from exc


def extract(invoice_text, mode):
    if not isinstance(invoice_text, str) or len(invoice_text.encode()) > 6000:
        raise ValueError("Cannot verify invoice: provide up to 6000 bytes of USD invoice text.")
    if mode not in {"live","mock"}:
        raise ValueError("Unknown extraction mode.")
    lines = [x.strip() for x in invoice_text.splitlines() if x.strip()]
    cited, usage = {}, {}
    if mode == "live":
        evidence, usage = _model_lines(invoice_text)
        if not isinstance(evidence, dict) or set(evidence) != set(LABELS):
            raise ValueError("Cannot verify all five model citations.")
        for field, source in evidence.items():
            if not isinstance(source, str) or lines.count(source) != 1 or source in cited:
                raise ValueError("Each candidate field requires one distinct verbatim invoice line.")
            cited[source] = field
    grounded, parsed = {}, {}
    currencies = []
    for line in lines:
        label, colon, value = line.partition(":")
        label, value = label.strip().casefold().rstrip("."), value.strip()
        field = next((k for k, names in LABELS.items() if label in names), None)
        if mode == "live" and line in cited:
            candidate = cited[line]
            hits = [key for key, anchor in ANCHOR.items() if re.search(anchor, label)]
            if field and field != candidate or not field and hits != [candidate]:
                raise ValueError("Source label conflicts with the proposed field: "+line[:100])
            field = candidate
        if not colon:
            raise ValueError("Unsupported invoice line: "+line[:100])
        if label == "currency":
            currencies.append(value.upper())
            continue
        if label in {"carrier","lane","invoice date","date","shipment"}:
            continue
        if not field or field in parsed:
            raise ValueError("Unsupported or repeated invoice line: "+line[:100])
        grounded[field] = line
        if field.endswith("_cents"):
            amount = re.fullmatch(r"(?:USD\s*|\$\s*)?((?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d{1,2})?)",value)
            if not amount:
                raise ValueError("Cannot verify USD amount: "+line[:100])
            parsed[field] = int(Decimal(amount[1].replace(",","")) * 100)
        elif re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_./-]{0,79}",value):
            parsed[field] = value
        else:
            raise ValueError("Cannot verify invoice or PO identifier.")
    if currencies != ["USD"] or set(parsed) != set(LABELS):
        raise ValueError("Cannot verify invoice: require USD, one invoice ID, PO, line haul, detention and total.")
    if mode == "live" and any(cited.get(line) != field for field, line in grounded.items()):
        raise ValueError("Model citations disagree with the verified invoice fields.")
    return {**parsed, "sources":grounded, "usage":usage}
