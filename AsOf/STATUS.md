# AsOf build status

Updated 2026-11-22 17:50. Mode is `MODE=replay` against `fixtures/live_check/`. Live credits spent: **7.8** (Phase 4 record run, user-approved; ledger `fixtures/live_check/ledger/phase4-record-2026-11-22.jsonl`).

## Phases
| Phase | State | Notes |
|---|---|---|
| 0 Check | ✅ done | `uv sync` ran; the crust client's 17 tests pass; `../.env` is present; agy is 1.5.14; `mcp` 2.3 and `pyyaml` 6.0 were added. |
| 1 Build | ✅ done | The engine, platform and pipeline are built. The UI was built by Antigravity in `frontend/`, `npm run build` passes, and it was reviewed and committed by the lead. |
| 2 Integrate | ✅ done | The full suite gives 146 passed + 1 xfail (C17). MCP over stdio lists the tools and answers C01. `clear delhivery.com` gives 5 cited lines in about 0.2 s. |
| 3 Council | ✅ gate PASS (rounds 1535, 1655 and final 1742) | 1519 BLOCKED (4 FAIL) → fixes → 1526 → 1531 → 1535 all 5 PASS. After Phase 4: 1655 all 5 PASS. After the final cleanups: 1742 all 5 PASS; full suite 195 passed. |
| 4 Live data | ✅ done (7.8 credits) | identify drl.aero 0.2; `clear` delhivery.com / tciexpress.in / shreebalajigrp.com 2.2 each; one page fetch 1.0. Recordings merged into `fixtures/live_check/cache`. **C17 settled as CANNOT_RESOLVE**: drl.aero matches Delhivery (5798) and Delhivery Robotics (15944579). Resolver no longer treats an `all_domains` alias as proof; ReplayIndex deleted. `/web/fetch` is a 404; the page fetch is `/web/enrich/live`, 1 credit/page. `inr_per_usd` 94.12 (OFX, dated 2026-10-21) → ₹62.12 per clearance file. Full suite 183 passed, 0 xfail. |
| 5 Docs and demo | ✅ done | agy is not installed here, so asof-docs (fallback) wrote README.md, docs/architecture.md (mermaid), docs/demo.md. Lead reviewed and rehearsed all 5 beats in replay, including the kill (chaos PASS). Open: Beat 1's raw-Crustdata-MCP contrast must be captured by a person in Claude with the Crustdata MCP added. |

## Demo beats (SPEC §10), in replay
| Beat | State |
|---|---|
| 1. "Shree Balaji Logistics" → CANNOT_RESOLVE, 25 candidates, needs a domain | ✅ |
| 1b. `resolve drl.aero` → CANNOT_RESOLVE, 2 candidates (the hardest case) | ✅ |
| 2. `clear delhivery.com` → 5 cited lines; cost 0 spent plus a recorded 2.2 credits / ₹62.12 | ✅ cost_note: "₹0.00 spent this run (replay); ₹62.12 measured cost of the stored copies (2.2 credits)" |
| 3. TCI 2020-01-01 → 418 (from the 2019-12-30 point); 2026-10-15 → STALE_DATA (38 days) | ✅ |
| 4. Approve, kill mid-send, restart → sent exactly once | ✅ The chaos harness passes on the real issue path. |
| 5. Watcher `/test` fires → a line goes STALE | ✅ watch → approve → issue → watch_test marks the headcount line STALE; a repeat test is a no-op |

## Council 1519 findings and their state
- **Engine (facts):** existence is now dated, attested statements now match the config template exactly, and ratio detection matches whole tokens. ✅ Fixed and committed (f587c55, 99 engine tests).
- **Platform (safety + robustness):** ✅ fixed and committed (49 platform, crust and e2e tests).
  - Remove MCP `approve`, so approval is human-only via the CLI.
  - Add MCP `issue` and `cost`.
  - `execute` refuses actions that weren't approved; add the `exceed_budget` hold.
  - The webhook must be https.
  - The person endpoints are switched off.
  - Replay watcher test.
  - Heal torn JSONL tails; the ledger skips bad lines.
  - Add identify pricing.
  - The outbox dedupes by key.
  - A state file with wrong-typed fields counts as torn.
  - Malformed 2xx bodies aren't cached.
- **Pipeline (e2e + safety + robustness):** ✅ fixed and committed. The full suite gives 180 passed + 1 xfail.
  - Wire watch → approve → test → STALE end to end.
  - Record the approver and timestamp.
  - Add a cross-process ledger view with a ₹ label.
  - Resolve accepts a positional name.
  - A stable ledger run_id across restarts.
- **Lead:** ✅ done.
  - The agy runner now scans the whole repo, fingerprints `../.env` and needs two flags to skip permissions.
  - The MCP e2e test now expects no `approve`, and `issue` and `cost` instead.

## Antigravity (agy) lane
- **Fixed in the runner:** it now creates the log dir, attaches the prompt to `--print=`, gives per-session `--settings` permissions, exits 2 when nothing was produced, takes an `AGY_TIMEOUT` override, and allows full permissions only with an explicit user OK.
- **Bottlenecks we found:**
  - Headless mode silently denies commands and doesn't name the one it denied.
  - agy waits for its own background tasks: it hung for 25 minutes after `npm install` finished.
  - There's no progress output until it exits.
- **UI result:** the full-permission continue run built `frontend/src` and `dist`, scope was checked clean (nothing outside `frontend/`), and ../.env was untouched.
- **Incident:** the lead edited `run_task.sh` while a run was executing it. Bash read the changed file from its old position and launched a second agy run, which the lead stopped by PID. Rule: never edit `agy/run_task.sh` while a run is in flight.
- **Timeout:** agy ignored its own `--print-timeout 600s`. Watch the elapsed time and stop it by PID (`pgrep -x agy`, never `pkill -f`, which matches the lead's own shell).

## UI review (lead)
- `demo_casefile.json` was regenerated from real `clear delhivery.com` CLI output: existence is dated, and cost reads 0 spent + ₹62.12 measured (2.2 credits at inr_per_usd 94.12).
- The cost panel was relabelled from "Total Fee (estimate)" to "Spent this run" and "Measured cost of this file". The ₹600 price is the only figure marked as an estimate.
- The C02, C07 and C08 refusal fixtures match the hidden cases. No "was true on" wording anywhere.
- ✅ Every UI fixture (4 timeline case files, C02/C07/C08, main case file) is now regenerated from replay CLI output by `frontend/fixtures/regen_fixtures.py`. The UI stays fixture-only for the demo (user decision).

## Final cleanups (2026-11-22, after Phase 4), all committed
- The webhook posts only to https hosts in the new config key `sandbox.allowed_hosts` (empty = outbox only).
- Ledger intent lines are fsynced before each live call, so a torn tail or a kill mid-call overcounts at worst and never undercounts the cap.
- Recorded unit costs are read from the recorded ledgers (identify 0.2, enrich 2.0), not hard-coded.
- Config keys are required everywhere (engine, platform, pipeline). A missing key raises an error naming it, instead of being misread as SOURCE_UNAVAILABLE.
- Person-endpoint branches are removed; the agy runner streams JSON progress.
- **Build complete:** every "Done means" item in CLAUDE.md is met. The one open item needs a person: capture the raw Crustdata MCP on "Shree Balaji Logistics" for demo Beat 1.
