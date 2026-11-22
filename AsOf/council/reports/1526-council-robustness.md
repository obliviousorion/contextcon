VERDICT: PASS

FINDINGS (re-check of 1519; all 8 fixes verified, no blocking items):
1. backend/crust/ledger.py:~62 (minor, non-blocking) — if the kill tears the LAST ledger line, that one charge is lost, because total = last intact cumulative. The cap undercounts by at most one call. Cause: the charge is written after the call returns. Fix, optional: write the entry before the network call, or state this in the README.
2. tests/platform/demo_actions.py — it uses the payload key "key", but the real issue path uses "idempotency_key". The demo still passes the chaos harness. Fix, optional: align the key name, or note it.
3. Plain `python` lacks httpx; use `uv run python` for anything that imports backend.crust. The chaos commands in council/README.md should say `uv run`. Documentation only.

VERIFIED FIXES (evidence):
- Fix 1, effects torn tail: I wrote an effects.jsonl whose last line was `{"key":"b","acti` and appended key c. The append starts on a fresh line. read_jsonl returns [a, c] and skips the torn line. FIXED.
- Fix 2, ledger torn tail: I wrote a torn last line (and later `[1]` and `null`) and reloaded. The total stayed at 4.0 with 2 entries, an append gave 6.0 with 3 entries, and the garbage lines were skipped. No crash, and the append heals the tail. FIXED.
- Fix 3, stable run ids: api.py:45 uses rq-<sha> and api.py:240 uses cf-<sha>. session.use_run binds the ledger file, so a restart reads the same ledger and the cap carries over. FIXED.
- Fix 4: crust/ledger.py PRICES has /company/identify at 0.2 per match. FIXED.
- Fix 5: sandbox_send dedupes on idempotency_key (actions.py:142). Chaos shows 1 outbox line per run. FIXED.
- Fix 6, wrong-typed state: runstate.load_state flagged torn=True for elapsed:"x", steps:[], holds:"2" and a truncated file. It quarantines the file to .torn and restarts clean. FIXED.
- Fix 7, malformed 2xx enrich: client.py:219 and :221 return unavailable ("malformed response"). The pipeline tests pass. FIXED.
- Fix 8: `python tests/platform/demo_actions.py` runs without PYTHONPATH. Chaos seed 11, 5 rounds, --expect-keys 3: effects=3 distinct=3, PASS. FIXED.

FAILING TESTS: none. `MODE=replay uv run pytest -q` gives 181 passed, 1 xfailed. The xfail is the C17 identify case, which needs a live record-mode call, as expected.

CHAOS (real issue path, MODE=replay, scratch script runs clear delhivery.com -> approve CF-id -> issue CF-id, --expect-keys 1):
- Seeds 1 to 5, 5 rounds, max-delay 4s: PASS in all (effects=1 distinct=1 torn=0). Most rounds finished before the kill, so these kills were sparse.
- Seeds 6, 7, 8, 5 rounds, max-delay 0.9s: all 5 rounds in each run were killed (kills at 0.05 to 0.87s) and all three PASS. Each has effects=1 distinct=1, and the outbox has exactly 1 line.
- Not re-run, same code path as 1519: cap lowered mid-run gives BUDGET_HELD and resumes, a mocked timeout gives SOURCE_UNAVAILABLE, and empty, garbage or unknown-domain requests give clean errors. The suite covers these and still passes.
