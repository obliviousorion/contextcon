VERDICT: PASS
FINDINGS:
1. backend/crust/ledger.py:17 — fallback `0.30 * 88` duplicates thresholds and is now stale (config inr_per_usd is 94.12), so a config read failure silently misprices the ledger — drop the fallback and let it raise, or read the config values.
2. backend/crust/ledger.py:21 — DEFAULT_CREDIT_CAP = 400.0 hard-coded outside config loading (same pattern at backend/pipeline/session.py:63 and backend/platform/config.py:29, default 40) — pre-existing, already in TODO; index the config keys without defaults.
3. backend/platform/actions.py:12,150 — urllib outside backend/crust/. Not a Crustdata call (sandbox webhook, https only, env URL); unchanged since the last gate — acceptable, but document the env var as trusted or add the allow-list already in TODO.
4. NOTES.md:5-10 — "Open items at handoff" are stale after Phase 4: C17 is settled as CANNOT_RESOLVE, web/fetch is measured (/web/enrich/live, 1 credit/page), CREDIT_TO_INR is config-driven, and the ReplayIndex is gone. Mark them resolved so no change request looks open.
5. TODO.md:20-24,38 — Phase 4 boxes (C17 identify, web fetch, per-company recordings, inr_per_usd, ReplayIndex delete) are done but unchecked; "remove dead person prices" is also done in ledger.py — tick them.
6. backend/crust/client.py:270 — comment says "/web/fetch returns 404", fine; but `autocomplete` path is still marked UNVERIFIED (client.py ~:274) — settle or leave in NOTES.
CHECKS:
- models.py: no change since f72d24b. config.yaml: 1 line (inr_per_usd 94.12), in lead commit 8a72c2d by the repo user (no other commits touch it) — OK.
- Module boundaries: the lead commit touched crust, pipeline, tests/*, README and docs only; no cross-folder edits by module agents. OK.
- Crustdata calls: all go through backend/crust/client.py; no httpx or requests outside crust (only item 3). session.py ReplayIndex bypass (council 1519 item 4) is deleted — resolved.
- Filters: filters.py rejects >= and <= (emits => and =<); no violations.
- Cross-module signatures use models.py types; resolver `_register` change is internal (Session.entity_by_id).
FAILING TESTS: none. .venv pytest, 183 passed (replay mode; no live calls made, .env untouched).
