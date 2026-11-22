# NOTES — change requests and open items
Agents append requests here; only the lead edits `backend/models.py` and `config.yaml`.

## Phase 4 results (2026-11-22, lead)
- C17 SETTLED: record-mode identify on drl.aero returned Delhivery (5798) and Delhivery Robotics (15944579), both at confidence 1.0. C17 is now CANNOT_RESOLVE. An `all_domains` alias is no longer proof: each new domain gets its own identify.
- `/web/fetch` is a 404 (free). The page fetch is `/web/enrich/live` at 1 credit/page (balance -1.0). `web_fetch` now calls it.
- Per-company recordings are merged into `fixtures/live_check/cache`; the ReplayIndex is deleted.
- `CREDIT_TO_INR` is config-driven: 0.30 × 94.12 = ₹28.24/credit.

## Open items at handoff (2026-11-22, superseded by Phase 4 above)
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

## From asof-platform (Phase 1, 2026-11-22), lead triage
- `tests/platform/` has no `__init__.py`, because a package named `platform` would shadow the stdlib module. Other test dirs must not reuse test-file basenames.
- mcp 2.3 is installed and exposes `MCPServer`; the server handles both that and 1.x `FastMCP`. No pin.
- Phase 2 wiring: the pipeline must use `actions.execute_approved` for every irreversible step, `watchers.create`/`activate`, `runstate.run(cost_fn=client.get_run_cost)` and `ledger.cost_summary(run_id)` for `CaseFile.cost`.
- Known window: a kill after `fn()` returns but before the effects line is appended could re-run `fn` on restart. Every `sandbox_send` payload must carry its idempotency key so the receiver dedupes.
- The stdio protocol path is still unverified (only tested in-process); Phase 2 runs C01 through a real MCP client.
