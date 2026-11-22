# AsOf TODO

Ordered by what unblocks "done". See `STATUS.md` for where each item stands.

## Now: council round 1519 fixes
- [x] platform: the safety and robustness fix list (49 tests; the live watch_create body is a guess and needs checking against the docs)
- [x] pipeline: beat 5 (watch → STALE), approval record, ledger view and ₹ label, stable run_id, `resolve` with a positional name (33 tests)
- [x] engine: existence dated, exact template, whole-token ratio check
- [x] lead: agy runner guards; MCP e2e test updated
- [x] lead: full suite, commit, re-run the reviewers; gate 1535 PASS

## UI (Antigravity)
- [x] agy finishes `frontend/src` and `npm run build` passes
- [x] lead review: only `frontend/` changed, the main fixture is regenerated from the CLI, cost relabelled, no "was true on" wording
- [ ] regenerate the 4 timeline case files in `frontend/fixtures/demo_refusals.json` from CLI dispute/clear output
- [ ] point the UI at the real API (VITE_API_URL) or keep it fixture-only for the demo (decide)
- [x] commit the frontend

## Phase 4: live data (needs the user's OK, about 15 credits, MODE=record)
- [ ] `company/identify drl.aero` → settles C17 and removes its xfail
- [ ] one `web/fetch`, to measure its credit cost
- [ ] a recorded per-company run for each demo company (removes the need for the ReplayIndex fallback)
- [ ] commit the recorded fixtures
- [ ] set `inr_per_usd` from a real rate (lead-owned config key)

## Phase 5: docs and demo
- [ ] agy: `agy/tasks/docs.md` with the test and ledger numbers appended → README.md, docs/ (mermaid diagram, demo script, business case)
- [ ] fallback: asof-docs if agy exits 2
- [ ] the README states the webhook caveat (receiver dedupes on idempotency_key) and labels the fee as an estimate
- [ ] rehearse the 2-minute demo in replay, including the kill mid-send

## Non-blocking cleanups (from the council)
- [ ] the webhook has no host allow-list (https only today); add a sandbox hosts config key (lead) or document the env var as trusted
- [ ] remove the dead person-endpoint prices in backend/crust/ledger.py
- [ ] a torn last ledger line loses that one charge (the cap undercounts by at most one call)
- [ ] index config keys without fallback defaults (platform config.py, watchers.py, engine rules.py, pipeline session.py)
- [ ] read the recorded unit costs from the ledger fixture instead of hard-coding them
- [ ] delete the ReplayIndex after the Phase 4 per-company recordings
- [ ] the agy runner uses `--output-format stream-json` so its progress is visible
