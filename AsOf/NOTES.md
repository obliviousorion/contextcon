# NOTES — change requests and open items
Agents append requests here; only the lead edits `backend/models.py` and `config.yaml`.

## Open items at handoff (2026-11-22)
- C17 (drl.aero → Delhivery id 5798) is UNVERIFIED and needs one record-mode `company/identify` call (0.2 credits).
- The `web/fetch` credit cost hasn't been measured.
- `job/search` returned HTTP 400 with our guessed request body. It's unused by design; if you want it, fix the body from docs.crustdata.com first.
- `backend/crust/ledger.py` has `CREDIT_TO_INR = 8.0`, which is wrong; asof-platform makes it config-driven.
- `fixtures/live_check/cache/` holds the cached raw responses that the client replays: identify (2 domains, 1 name), enrich (3 companies), permissions, autocomplete.
