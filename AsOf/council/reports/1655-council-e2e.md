VERDICT: PASS
FINDINGS (all in MODE=replay, fresh mktemp state dirs, ASOF_TODAY=2026-11-22; no live calls):
1. `clear delhivery.com` — CaseFile, >=4 cited lines, cost in Rs, <10 s — got 5 attested lines each with evidence ids, cost Rs 0.00 spent / Rs 62.12 (2.2 credits) recorded, 0.27 s. OK.
2. `dispute tciexpress.in 2020-01-01` — headcount 418 — got attested 418 (point 2019-12-30). OK.
3. `dispute tciexpress.in 2026-10-15` — STALE_DATA — got cannot_attest STALE_DATA, gap_days 38. OK.
4. `resolve "Shree Balaji Logistics"` — CANNOT_RESOLVE, 25 candidates — got cannot_resolve, 25, missing "a domain". OK.
5. `audit tciexpress.in` growth claim — cannot_verify with both values — got cannot_verify (NO_RECORD_TYPE), side-by-side 416 / later value in reason; a dated 1715 claim got agree. OK.
6. MCP stdio (`backend.platform.mcp_server`) — 10 tools listed (resolve, attest, clear_counterparty, dispute_file, observe, audit_claims, request_evidence, watch, issue, cost); `attest tciexpress.in headcount 2020-01-01` — attested 418, is_error False. OK.
7. New Phase 4 checks — `resolve drl.aero` gives cannot_resolve with Delhivery 5798 and Delhivery Robotics 15944579; `resolve delhivery.com` gives resolved 5798; an unrecorded domain gives cannot_resolve "replay_miss ... no network" (no network, no ReplayIndex fallback); Rs 28.24/credit arithmetic matches (2.2 cr = Rs 62.12; alert 5 cr = Rs 141.18); ledger sums 7.8 credits. OK.
8. Issue flow — issue before approve = held_for_approval; approve; issue = done; issue again = same key; effects.jsonl = 1 line; sandbox only. Watch: held, approve, issue, watch_test = alert, repeat = no_op. OK. Chaos seed 7: effects=3 distinct=3 torn=0, outbox 3 lines, CHAOS: PASS.
9. docs/demo.md walked beat by beat; all outputs match, including dispute delhivery.com 2022-06-01 (headcount/revenue_band NOT_YET_RECORDED) and `observe` 418 vs 1715.
10. docs/demo.md:15 — Beat 1 step 1 still carries "TODO(lead): capture it" (no recorded raw-Crustdata-MCP answer exists in the repo) — presenter has nothing to show for the "before" half of the demo — capture/attach the recording or reword the beat to a spoken contrast. (Low; not a code defect.)
11. docs/demo.md Close — `asof cost` shows empty case_files / 0 recorded credits in a state dir that has no case files (e.g. after the Beat 5 fresh dir, before `clear` runs it is empty) — note that cost is only populated after a clear in the same state dir. (Low; clarity.)
FAILING TESTS: none. `uv run pytest -q`: 183 passed in 5.4 s.
