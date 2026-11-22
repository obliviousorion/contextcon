"""Synthetic sources for the November refrigerated freight settlement demo."""


def sample(missing: bool = False) -> dict:
    suffix = "18" if missing else "17"
    po_id = f"PO-604{suffix}"
    invoice = f"""Carrier: Juniper Freight Co.
Lane: Dallas, TX to Tulsa, OK
Currency: USD
Invoice ID: JF-82{suffix}
PO: {po_id}
Linehaul: $2,400.00
Detention: $450.00
Total due: $2,850.00"""
    return {
        "case_id": f"FC-10{suffix}",
        "po_id": po_id,
        "contracted_base_cents": 240000,
        "detention_cents_per_hour": 15000,
        "free_minutes": 60,
        "pod_minutes": None if missing else 120,
        "invoice_text": invoice,
    }
