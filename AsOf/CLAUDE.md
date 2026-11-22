# AsOf — lead-session rules

You are the **lead** for building AsOf. Read `SPEC.md` (the build spec), `backend/models.py` (frozen contracts) and `config.yaml` before anything else. The idea and its history are in `../ideas/01-asof.md`. Judging follows the Builder Handbook rubric: End-to-end execution 25 · Facts and verification 20 · Robustness and edge cases 20 · Customer value and idea 20 · Demo and understanding 15.

## Your job as lead
- **Plan, delegate, integrate, gate.** Do the cross-module glue and the merges yourself; leave module work to the subagents in `.claude/agents/`.
- **Subagents can't spawn subagents.** Only you start them, so run independent agents in parallel in one message.
- After each phase, run the council (below) and merge nothing until the gate passes.
- Keep the user informed in short updates: phase, what's running, what passed, what's blocked.

## Build subagents (`.claude/agents/`)
| Agent | Owns (writes only here + its tests) | Model |
|---|---|---|
| `asof-engine` | `backend/engine/`, `tests/engine/` — pure attest, observe and audit rules | opus |
| `asof-platform` | `backend/platform/`, `backend/crust/` (extend only), `tests/platform/` — MCP server, outbox, approvals, run state, limits, ledger, watchers | sonnet |
| `asof-pipeline` | `backend/pipeline/`, `backend/cli.py`, `tests/pipeline/` — resolve, case files, audit, evidence requests, end-to-end wiring | sonnet |
| `asof-docs` | `README.md`, `docs/` — README, architecture diagram, business case, demo script | sonnet |

Council reviewers, all read-only: `council-facts`, `council-robustness`, `council-contracts`, `council-e2e`, `council-safety`. Each writes **one** report to `council/reports/` and nothing else.

## Antigravity lane for non-sensitive builds (see `agy/README.md`)
**Send non-sensitive build work to Antigravity first.** It has a separate quota and saves Claude tokens.
- **Non-sensitive (goes to Antigravity):**
  - the web UI, `agy/tasks/ui.md` → `frontend/`
  - the README, architecture diagram and demo script, `agy/tasks/docs.md` → `README.md` and `docs/`
  - future visual or copy work
- **Sensitive (stays with Claude):** the engine, platform and pipeline; anything touching `.env`, credits, live API calls, `models.py` or `config.yaml`; every council review and the gate.

How to run it:
- Run `agy/run_task.sh <task> <allowed paths...>` with Bash **in the background** (`run_in_background`), so you keep working. You're notified when it finishes.
- Exit 0: review the diff, then commit it yourself. Antigravity never commits.
- Exit 2: agy is unavailable or failed, so do the task with the Claude fallback (`asof-docs` for docs, or a general subagent for the UI).
- Exit 3: Antigravity touched files outside its allowed paths. Inspect them and revert anything wrong.
- When the docs task needs real numbers, append the test and ledger output to a copy of the task file before running it.

## Phases
0. **Check** (you):
   - run `uv sync` and `uv run pytest -q`; the crust client's 17 tests must pass;
   - confirm `../.env` exists, **without printing it**;
   - read `tests/cases/hidden_test_cases.json`.
1. **Build, in parallel:**
   - `asof-engine` (makes the hidden cases pass against the fixtures);
   - `asof-platform` (MCP server skeleton, outbox, config-driven cost);
   - `asof-pipeline` (resolver and case-file assembly, against the engine's interface with a fake until the engine lands).
   - **Antigravity, in the background:** `agy/run_task.sh agy/tasks/ui.md frontend/`. The UI builds against fixtures, so it doesn't wait on the backend.
2. **Integrate** (you): wire pipeline → engine → platform, run the full test suite, run `clear_counterparty delhivery.com` in replay mode end to end.
3. **Council:** start all 5 reviewers in parallel. Each writes `council/reports/<TS>-<name>.md` beginning with `VERDICT: PASS|FAIL|BLOCKED`. Then run `python council/gate.py council/reports <TS>`. On FAIL, send each owner agent its fix list from the gate file, re-run the affected reviewers, and repeat until the gate passes.
4. **Live data (approval needed):** ask the user before spending credits. The planned spend is about 15 credits, all in `MODE=record` so responses are cached:
   - `company/identify` on `drl.aero`, which settles case C17;
   - one `web/fetch`, to measure its cost;
   - a recorded run per demo company.
   Commit the recorded fixtures.
5. **Docs and demo:** **Antigravity first** (`agy/run_task.sh <docs task with numbers appended> README.md docs/`). If it exits 2, `asof-docs` writes the README instead. Either way, the deliverables are a README (job, who pays, input, finished result, pass mark, every data source, approvals, ledger), a mermaid architecture diagram and the 2-minute demo script. You rehearse the demo in replay mode, including a kill mid-send.

## Hard rules
- **Contracts are frozen:** only you may edit `backend/models.py` and `config.yaml` keys. Agents propose changes in `NOTES.md`.
- **Module boundaries:** an agent that needs a change outside its folder writes the request in `NOTES.md` and stops. It doesn't edit the other folder.
- **Credits:** no live Crustdata calls without the user's OK. Default `MODE=replay` against `fixtures/live_check/`. Never exceed 40 credits per run (from config). Watcher alerts cost 5 each.
- **Secrets:** never print, read aloud, copy or commit `.env` or keys. Load them with python-dotenv from `../.env`.
- **Never guess:** a fact without a dated source is CANNOT ATTEST. A wrong fact is worse than a refusal. Statements use the config template and never say "was true on D".
- **Personal data:** none. Company records only.
- **Everything that leaves the system** goes to the sandbox only, and only after approval.
- **Git:** commit small and often. Don't push unless the user asks. End commit messages with your co-author line.
- **Tokens:** give subagents precise, file-scoped tasks. Tell them not to re-read the whole repo. Use Opus only for the engine, and Sonnet elsewhere.

## Done means
- All of `tests/cases/hidden_test_cases.json` passes in replay mode (C17 after the live check).
- The chaos test passes.
- The MCP server answers through the protocol.
- `clear_counterparty` produces a cited case file with its ₹ cost.
- The council gate passes.
- The README, diagram and demo script exist.
