"""Deterministic freight payables policy. Actions are intents for a sandbox ledger."""


def _integer(value):
    # bool is an int subclass. Reject it along with floats and numeric strings.
    return type(value) is int and 0 <= value <= 10**12


def _identifier(value):
    return isinstance(value, str) and 0 < len(value.strip()) <= 120 and value.isprintable()


def _money(cents):
    units, fraction = divmod(cents, 100)
    return f"{units:,}.{fraction:02d}"


def run_case(packet: dict, extraction: dict, resolution: str | None = None) -> dict:
    """Audit a single invoice against a single contract and proof of delivery.

    A resolution is an annotation. Corrected evidence must pass every original
    check. Callers persist these intents atomically and enforce invoice uniqueness.
    """
    trace = []
    lines = []  # Line-item audit: billed, supported and withheld amounts per charge.

    def record(step, reason, *sources):
        trace.append({"step": step, "reason": reason, "sources": list(sources)})

    def hold(reason, *sources):
        record("Hold for review", reason, *sources)
        return {"status": "REVIEW", "payable_cents": 0, "recovered_cents": 0,
                "trace": trace, "actions": [], "lines": lines}

    if not isinstance(packet, dict) or not isinstance(extraction, dict):
        return hold("Supply the packet and its extracted invoice fields.", "Intake")
    if not _identifier(packet.get("case_id")) or not _identifier(packet.get("po_id")):
        return hold("A case ID and contract purchase order ID are required.", "Intake", "Contract")
    if not isinstance(packet.get("invoice_text"), str) or not packet["invoice_text"].strip():
        return hold("Attach the carrier invoice text before settlement.", "Intake.invoice_text")

    case_id = packet["case_id"].strip()
    contract_po = packet["po_id"].strip()
    contract = f"Contract {contract_po}"
    proof = f"POD for {case_id}"
    if resolution:
        record("Reopen evidence", str(resolution), f"Reviewer note for {case_id}")
    for key in ("invoice_id", "po_id"):
        if not _identifier(extraction.get(key)):
            return hold(f"The invoice needs an unambiguous {key}.", f"Invoice for {case_id}")

    invoice_id = extraction["invoice_id"].strip()
    invoice = f"Invoice {invoice_id}"
    if extraction["po_id"].strip() != contract_po:
        return hold(f"Invoice cites {extraction['po_id']}. The contract cites {contract_po}. "
                    "Supply the matching documents.", invoice, contract)
    record("Match purchase order", f"Invoice and contract both cite {contract_po}.", invoice, contract)

    for data, keys, source in (
        (extraction, ("base_cents", "detention_cents", "total_cents"), invoice),
        (packet, ("contracted_base_cents", "detention_cents_per_hour", "free_minutes"), contract),
    ):
        for key in keys:
            if not _integer(data.get(key)):
                return hold(f"Check {key}. Expected a nonnegative whole number within the "
                            "supported range (0 to 1 trillion).", source)

    base = extraction["base_cents"]
    detention = extraction["detention_cents"]
    total = extraction["total_cents"]
    if total != base + detention:
        return hold(f"Base {_money(base)} plus detention {_money(detention)} equals "
                    f"{_money(base + detention)}. Invoice total is {_money(total)}. "
                    "Reconcile the difference before posting.", invoice)
    record("Reconcile invoice", f"Base {_money(base)} + detention {_money(detention)} "
           f"= invoiced total {_money(total)}.", invoice)

    base_cap = packet["contracted_base_cents"]
    approved_base = min(base, base_cap)
    record("Price line haul", f"Billed {_money(base)}. Contract cap {_money(base_cap)}. "
           f"Allow {_money(approved_base)}, the lower amount.", invoice, contract)
    lines.append({"charge": "Line haul", "billed_cents": base, "supported_cents": approved_base,
                  "withheld_cents": base - approved_base,
                  "basis": f"Lower of billed and contract rate {_money(base_cap)}"})

    minutes = packet.get("pod_minutes")
    if minutes is not None and not _integer(minutes):
        return hold("The proof of delivery needs a valid nonnegative dwell time in minutes.", proof)
    if minutes is None and detention:
        lines.append({"charge": "Detention", "billed_cents": detention, "supported_cents": None,
                      "withheld_cents": None, "basis": "Awaiting verified dwell minutes"})
        return hold(f"The carrier billed {_money(detention)} detention. Attach verified "
                    "dwell minutes to calculate the contractual allowance.", invoice, contract, proof)
    if detention:
        free = packet["free_minutes"]
        rate = packet["detention_cents_per_hour"]
        hours = max(0, minutes - free) // 60
        allowance = hours * rate
        approved_detention = min(detention, allowance)
        record("Price detention", f"{minutes} recorded minutes less {free} free minutes "
               f"yields {hours} complete billable {'hour' if hours == 1 else 'hours'} "
               f"at {_money(rate)} per hour. "
               f"Cap {_money(allowance)}, billed {_money(detention)}, "
               f"allow {_money(approved_detention)}.", proof, contract, invoice)
        basis = (f"{minutes} min dwell − {free} free = {hours} billable "
                 f"{'hour' if hours == 1 else 'hours'} × {_money(rate)}")
    else:
        approved_detention = 0
        record("Price detention", "The invoice claims zero detention. Allow 0.00.", invoice)
        basis = "No detention billed"
    lines.append({"charge": "Detention", "billed_cents": detention,
                  "supported_cents": approved_detention,
                  "withheld_cents": detention - approved_detention, "basis": basis})

    payable = approved_base + approved_detention
    recovered = total - payable
    sources = [invoice, contract] + ([proof] if detention else [])
    reason = (f"Post {_money(approved_base)} line haul + {_money(approved_detention)} "
              f"detention = {_money(payable)} payable. Withhold {_money(recovered)} "
              f"from the billed {_money(total)}.")
    record("Settle in sandbox", reason, *sources)
    shared = {"invoice_id": invoice_id, "case_id": case_id, "reason": reason, "sources": sources}
    actions = [
        {**shared, "type": "LEDGER_POST", "amount_cents": payable},
        {**shared, "type": "SHORT_PAY_NOTICE" if recovered else "REMITTANCE_NOTICE",
         "amount_cents": recovered if recovered else payable},
    ]
    return {"status": "SETTLED", "payable_cents": payable, "recovered_cents": recovered,
            "trace": trace, "actions": actions, "lines": lines}
