# AsOf TODO

Ordered by what unblocks "done". See `STATUS.md` for where each item stands.

## Now: council round 1519 fixes
- [x] platform: the safety and robustness fix list (49 tests; the live watch_create body is a guess and needs checking against the docs)
- [ ] pipeline: beat 5 (watch → STALE), approval record, ledger view and ₹ label, stable run_id, `resolve` with a positional name
- [x] engine: existence dated, exact template, whole-token ratio check
- [x] lead: agy runner guards; MCP e2e test updated
- [ ] lead: full suite, commit, re-run the 4 failed reviewers (facts, safety, e2e, robustness), gate until PASS

## UI (Antigravity)
- [ ] agy finishes `frontend/src` and `npm run build` passes
- [ ] lead review: only `frontend/` changed, fixture values match `enrich.json` and the hidden cases, no "was true on" wording, labels present
- [ ] commit the frontend

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
- [ ] index config keys without fallback defaults (platform config.py, watchers.py, engine rules.py, pipeline session.py)
- [ ] read the recorded unit costs from the ledger fixture instead of hard-coding them
- [ ] delete the ReplayIndex after the Phase 4 per-company recordings
- [ ] the agy runner uses `--output-format stream-json` so its progress is visible
