VERDICT: PASS

Re-check of 1519 fixes (fb4e427, fbc0527), MODE=replay, temp ASOF_STATE_DIR.
1. Beat-5 flow — OK: clear -> watch (key watch:7cbabb3c..., held_for_approval) -> approve --by Asha (approved_by/approved_at recorded) -> issue (w-7cbabb3cf831) -> watch_test alert with stale_line_ids [CF-38e15ccbbde1#headcount] -> show flags headcount line stale=true with stale_note and a stale[] block -> second watch_test no_op (duplicate signal date).
2. cost across processes — OK: separate process lists CF-38e15ccbbde1, 0.0 spent, recorded 2.2 credits / Rs58.08; cost_note matches the required text exactly.
3. Positional resolve "Shree Balaji Logistics" — OK: cannot_resolve, 25 candidates.
4. audit --help — OK: documents --claims schema, fields and an example.
5. MCP — uv run pytest -q tests/e2e: 2 passed (issue and cost exposed, no approve).
6. Minor, not blocking: watch_test current_line statement says "stored copy retrieved ..." with signal_date = today (replay); acceptable.
FAILING TESTS: none in tests/e2e. C17 known xfail. Demo script/README/UI deferred to Phase 5.
