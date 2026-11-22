# AsOf TODO

Ordered by what unblocks "done". See `STATUS.md` for where each item stands.

## Done: council round 1519 fixes
- [x] platform: the safety and robustness fix list (49 tests; the live watch_create body is a guess and needs checking against the docs)
- [x] pipeline: beat 5 (watch → STALE), approval record, ledger view and ₹ label, stable run_id, `resolve` with a positional name (33 tests)
- [x] engine: existence dated, exact template, whole-token ratio check
- [x] lead: agy runner guards; MCP e2e test updated
- [x] lead: full suite, commit, re-run the reviewers; gate 1535 PASS

## UI (Antigravity)
- [x] agy finishes `frontend/src` and `npm run build` passes
- [x] lead review: only `frontend/` changed, the main fixture is regenerated from the CLI, cost relabelled, no "was true on" wording
- [x] regenerate the 4 timeline case files in `frontend/fixtures/demo_refusals.json` from CLI dispute/clear output
- [x] UI stays fixture-only for the demo (user decision, 2026-11-22)
- [x] commit the frontend

## Phase 4: live data (needs the user's OK, about 15 credits, MODE=record)
- [x] `company/identify drl.aero` → C17 settled as CANNOT_RESOLVE (two companies); xfail removed
- [x] one page fetch: `/web/fetch` is 404; `/web/enrich/live` is 1 credit/page
- [x] a recorded per-company run for each demo company (removes the need for the ReplayIndex fallback)
- [x] commit the recorded fixtures
- [x] set `inr_per_usd` from a real rate (lead-owned config key)

## Phase 5: docs and demo
- [x] agy: not installed in this environment (exit 2 path)
- [x] fallback: asof-docs wrote README.md, docs/architecture.md, docs/demo.md
- [ ] capture a real run of the raw Crustdata MCP on "Shree Balaji Logistics" for demo Beat 1 (a person, in Claude)
- [x] the README states the webhook caveat (receiver dedupes on idempotency_key) and labels the fee as an estimate
- [x] rehearse the 2-minute demo in replay, including the kill mid-send

## Non-blocking cleanups (from the council)
- [x] the webhook has no host allow-list (https only today); add a sandbox hosts config key (lead) or document the env var as trusted
- [x] remove the dead person-endpoint prices in backend/crust/ledger.py
- [x] a torn last ledger line loses that one charge (the cap undercounts by at most one call)
- [x] index config keys without fallback defaults (platform config.py, watchers.py, engine rules.py, pipeline session.py)
- [x] read the recorded unit costs from the ledger fixture instead of hard-coding them
- [x] delete the ReplayIndex after the Phase 4 per-company recordings
- [x] person-endpoint branches still exist in backend/crust/client.py `_estimate`/`_credits` (endpoints are hard-disabled; cleanup only)
- [x] the agy runner uses `--output-format stream-json` so its progress is visible

## Optional polish (council 1742 notes, non-blocking)
- [ ] the sandbox webhook uses a no-redirect opener (urllib follows redirects today)
- [ ] `DEFAULT_CREDIT_CAP = 400` in backend/crust/ledger.py is a fallback for a client built without config; make the config cap mandatory
- [ ] a failed live call releases its ledger intent, which assumes failed calls aren't billed; confirm with Crustdata
- [ ] demo Beat 5: print the watch handle so it doesn't have to be copied by hand
