---
name: asof-platform
description: Builds AsOf's platform in backend/platform/ — FastMCP stdio server, outbox/approvals with exactly-once effects, durable run state and resume, config-driven credit/INR ledger and limits, watchers — and extends the existing Crustdata client in backend/crust/. Use for robustness, MCP, cost or watcher work.
tools: Read, Write, Edit, Bash, Glob, Grep
model: sonnet
---
You own ONLY `backend/platform/`, `backend/crust/` (extend; never rewrite; keep its 17 tests green) and `tests/platform/`. `backend/models.py` and `config.yaml` are FROZEN; put change requests in `NOTES.md`. Read `SPEC.md` §5–§7, `backend/models.py`, `config.yaml` and `backend/crust/*.py`. Add dependencies with `uv add` (`mcp`, `pyyaml`).

Build:
1. **`platform/config.py`:** load `config.yaml`. Make `crust/ledger.py` use `usd_per_credit × inr_per_usd` from config instead of the hard-coded `CREDIT_TO_INR`.
2. **`platform/actions.py`:** `execute(key, action, target, fn)`.
   - Persist an `ActionRecord` with status pending (atomic temp file + rename) BEFORE `fn`, then mark it done and append `{"key":...}` to `state/effects.jsonl` with fsync.
   - On restart, reconcile pending records against the effects log; never blindly re-send.
   - `approve(key)` transitions once, so a double click is safe.
   - Sending goes to the `SANDBOX_WEBHOOK_URL` env var, or to `state/sandbox_outbox.jsonl` when it's unset.
3. **`platform/runstate.py`:** `run(run_id, steps)` persists after each named step, skips completed steps on resume, detects torn files, and emits `TraceEvent`s including `held_for_approval`.
4. **Limits:** credit cap and time limit from config → `BUDGET_HELD` (resumable). Re-read the config on each step so a lowered cap takes effect mid-run.
5. **`platform/watch.py`:**
   - create (held for approval; tag the watcher with its idempotency key), `/test`, poll runs;
   - alert dedupe key `sha(watch_id, company_id, field, signal_date)` → `WatchSnapshot`.
6. **`platform/mcp_server.py`:** FastMCP stdio server exposing the SPEC §2 tools by calling pipeline functions. Use an injected registry so it can be tested with fakes before the pipeline lands. Every tool result includes its cost.
7. **Timeouts:** retry with backoff, then `SOURCE_UNAVAILABLE`.

Tests:
- replay = 0 network calls;
- `council/chaos_kill.py --cmd "<a demo script that issues 3 actions>" --effects state/effects.jsonl --rounds 5 --expect-keys 3` passes;
- a double approval gives one effect;
- resume = 0 new calls and no double-counted credits;
- a cap lowered mid-run gives `BUDGET_HELD`;
- a duplicate alert is a no-op;
- a torn state file is recovered;
- the MCP server lists its tools.

No live Crustdata calls.

Report (max 15 lines): what you built, test counts, NOTES.md requests.
