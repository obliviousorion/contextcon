VERDICT: PASS

All commands ran in replay with ASOF_STATE_DIR set to a temp dir. Beats 1b to 5 produced the values the script gives. These are the cosmetic gaps:

1. docs/demo.md (Backup path 1 and README.md line 74) — both say "183 passed", but `uv run pytest -q` gives 195 passed (8.4 s). The README also says "about 6 seconds" for the suite. — update the counts to 195 and about 8 s.
2. docs/demo.md Beats 1, 1b, 2 and 3 — the script shows condensed, hand-formatted output. The CLI prints full pretty JSON. Examples: `asof clear` prints the whole case file, with `cost` and `cost_note` near the end; `resolve` prints the full 25-candidate JSON. The values match (CF-38e15ccbbde1; cost 0.0 credits and ₹0.00 spent; recorded 2.2 credits and ₹62.12; TCI 418 at 2019-12-30; STALE_DATA with gap_days 38). — add "(condensed; pipe through jq or head)" to the script, or the presenter should know to trim the output.
3. docs/demo.md Beat 1 step 1 — the raw Crustdata MCP contrast is marked only by an inline "TODO(lead): capture it". It is flagged, which satisfies the known-open-item rule, but it is easy to miss. — make it a visible callout such as "OPEN: to be captured live before the demo".
4. docs/demo.md Beat 5 — `W=watch:<hex>` has to be copied by hand from the `watch` output. The flow works when the real handle is used: held_for_approval, then approve, then issue (created, w-7cbabb3cf831), then watch_test gives alert with stale_line_ids ["CF-38e15ccbbde1#headcount"] and alert_cost_credits 5.0. A second watch_test gives no_op with "duplicate signal date (or monthly alert cap)". — optional: tell the presenter to run `W=$(asof watch delhivery.com | jq -r .watch_id_handle)`. Do this in a state dir where `clear` has run, because `watch` and `approve` look up state in the current ASOF_STATE_DIR.

Beats that passed:
- Beat 1: `resolve "Shree Balaji Logistics"` gives cannot_resolve, entity null, and the 25-candidate list.
- Beat 1b: `resolve drl.aero` gives cannot_resolve with the 2 candidates, Delhivery and Delhivery Robotics, and the "missing" text matches.
- Beat 2: `clear delhivery.com` has 5 attested, cited lines and ran in 0.45 s.
- Beat 3: `attest` for 2020-01-01 gives 418. For 2026-10-15 it gives STALE_DATA with gap_days 38. `dispute` and `observe` both run: observe returns 418 and 1715 with no growth verdict.
- Beat 4: `approve` returns first_approval true. `issue` run twice returns identical done output. effects.jsonl has 1 line. Chaos run with seed 7 matches the script exactly (kills at 0.29, 0.16, 0.54, 0.10 and 0.45 s; effects=3 distinct=3 torn_lines=0; CHAOS: PASS). sandbox_outbox.jsonl has 3 lines.
- Close: `asof cost` gives 0 spent and 2.2 recorded credits.

Other checks:
- `uv run pytest -q tests/e2e` gives 4 passed (MCP over stdio).
- Full suite: 195 passed.
- README quickstart (`uv sync`, pytest, the exports, `clear delhivery.com`) runs as written. The `claude mcp add` line was not executed.
- `cd frontend && npm run build` passes (built in 2.15 s).
- The backup-path file council/reports/1535-GATE.md exists.
