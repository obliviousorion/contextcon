# AsOf build status

Updated 2026-11-22 15:25. Mode is `MODE=replay` against `fixtures/live_check/`. Live credits spent this session: **0**.

## Phases
| Phase | State | Notes |
|---|---|---|
| 0 Check | ✅ done | `uv sync` ran; the crust client's 17 tests pass; `../.env` is present; agy is 1.5.14; `mcp` 2.3 and `pyyaml` 6.0 were added. |
| 1 Build | ✅ done, except the UI | engine, platform and pipeline are built and committed. The UI is in progress on Antigravity. |
| 2 Integrate | ✅ done | The full suite gives 146 passed + 1 xfail (C17). MCP over stdio lists the tools and answers C01. `clear delhivery.com` gives 5 cited lines in about 0.2 s. |
| 3 Council | 🔄 round 1519 BLOCKED, fixes in progress | contracts PASS; facts, safety, e2e and robustness FAIL. The fix lists are routed to their owners. |
| 4 Live data | ⏸ waits for user approval | About 15 credits in record mode. |
| 5 Docs and demo | ⏸ not started | Antigravity goes first; asof-docs is the fallback. |

## Demo beats (SPEC §10), in replay
| Beat | State |
|---|---|
| 1. "Shree Balaji Logistics" → CANNOT_RESOLVE, 25 candidates, needs a domain | ✅ |
| 2. `clear delhivery.com` → 5 cited lines; cost 0 spent plus a recorded 2.2 credits / ₹58.08 | ✅ (ledger view in progress) |
| 3. TCI 2020-01-01 → 418 (from the 2019-12-30 point); 2026-10-15 → STALE_DATA (38 days) | ✅ |
| 4. Approve, kill mid-send, restart → sent exactly once | ✅ The chaos harness passes on the real issue path. |
| 5. Watcher `/test` fires → a line goes STALE | ❌ being wired (pipeline + platform) |

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
- **Pipeline (e2e + safety + robustness):** in progress.
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
- **Current run:** continues the UI from its saved state, foreground commands only, 10-minute cap.
