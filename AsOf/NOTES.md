# NOTES — change requests and open items
Agents append requests here; only the lead edits `backend/models.py` and `config.yaml`.

## Open items at handoff (2026-11-22)
- C17 (drl.aero → Delhivery id 5798) is UNVERIFIED and needs one record-mode `company/identify` call (0.2 credits).
- The `web/fetch` credit cost hasn't been measured.
- `job/search` returned HTTP 400 with our guessed request body. It's unused by design; if you want it, fix the body from docs.crustdata.com first.
- `backend/crust/ledger.py` has `CREDIT_TO_INR = 8.0`, which is wrong; asof-platform makes it config-driven.
- `fixtures/live_check/cache/` holds the cached raw responses that the client replays: identify (2 domains, 1 name), enrich (3 companies), permissions, autocomplete.

## From asof-pipeline (Phase 1, 2026-11-22), lead triage
- **Replay cost shows ₹0.** Replay cache hits cost 0 credits, so `CaseFile.cost` reads ₹0 and the demo's "ledger shows ₹" fails. Lead decision pending in Phase 2: report the recorded run's cost from the fixture ledger, clearly labelled, without changing models.py if possible.
- **Batched fixture cache keys.** Recorded identify/enrich calls are batched, so the pipeline added a replay-only fallback index over `fixtures/live_check/cache`. Per-company record-mode runs in Phase 4 would remove the need for it.
- **C17** stays xfail until the approved `company/identify drl.aero` record call.
- **Ledger dir:** the pipeline writes `$ASOF_STATE_DIR/ledger`, while the crust default is `backend/crust/ledger`. Unify in Phase 2.
- **Guarded yaml import.** `session.py` falls back to built-in config defaults when yaml is missing. That fallback duplicates thresholds and must be removed once pyyaml is installed (council-contracts: thresholds come only from config.yaml).
- **Skipped company/search.** Autocomplete + identify-by-name lists candidates, so the paid search step is skipped (deviation from SPEC §4 step 1; saves credits, and C08 still gives 25).
