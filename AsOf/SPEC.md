# AsOf — build spec (source of truth for every agent)

> **"Crustdata gives you raw data. AsOf decides what it can swear to, and as of when."**

The idea and its council history are in `../ideas/01-asof.md` (#1 on the leaderboard, 88/100 on the Handbook rubric). This file is the **build** spec. Where they differ, this file wins. Contracts live in `backend/models.py`, which is FROZEN; change requests go in `NOTES.md`. Thresholds live in `config.yaml`.

## 1. The job
A firm onboarding a counterparty, such as a procurement team clearing a carrier or a credit team checking a borrower, needs to know what is provably true about that company. After a dispute, an insurer or arbitrator needs to know what was knowable about it **on a past date D**. AsOf takes a request in plain terms and returns a **finished case file**. Every line in it either:
- states what a dated record says, with its source, or
- says CANNOT ATTEST and names exactly what is missing.

It never guesses. A wrong fact is worse than "I can't verify".

**Finished results (Handbook E2E, 25 points):**
- **Clearance file:** an attestation as of today for a new counterparty.
- **Dispute file:** an attestation as of a past date D.
- **Audit report:** structured claims from someone else's report or deck, each graded agree / contradict / cannot verify.
- **Held evidence request:** when records can't settle it, a request for what's needed, labelled "Not a negative finding". Never a rejection.

## 2. Request types
Each is an MCP tool, a CLI command and, optionally, a UI action.

| Tool | Input | Output | Irreversible step (held for approval) |
|---|---|---|---|
| `resolve` | `name` or `domain` | `ResolveResult` | — |
| `attest` | `domain` or `id`, `field`, `as_of` | `AttestLine` | — |
| `clear_counterparty` | `domain` | `CaseFile(kind="clearance")`, as of today, all record types | `issue_case_file` |
| `dispute_file` | `domain`, `as_of` | `CaseFile(kind="dispute")` | `issue_case_file` |
| `observe` | `domain`, `field`, `d1`, `d2` | two `AttestLine`s side by side. **Never** a growth or ratio verdict | — |
| `audit_claims` | `domain`, `[ClaimInput]` (structured, no LLM splitting) | `AuditReport` | `issue_audit_report` |
| `request_evidence` | `target`, `items` | `EvidenceRequest` | `send_evidence_request` |
| `watch` | `domain` | watcher id. Each alert: re-attest today, `WatchSnapshot`, mark lines STALE | `create_watcher` (alerts cost 5 credits) |

## 3. Attestation rules (module `backend/engine/`: pure functions, no network)
Input: a company record dict (the shape of `fixtures/live_check/enrich.json[*].matches[0].company_data`), `field`, `as_of` D, `retrieved_at` T, and the config.

| Field | Rule |
|---|---|
| `headcount` | Take the latest `headcount.timeseries` point with date ≤ D. None → `NOT_YET_RECORDED` (name the first point's date). D minus point date > `max_staleness_days` → `STALE_DATA` (name the nearest point and the gap). Label "profile-derived count". |
| `existence` | `basic_info.year_founded` null → `CANNOT_ATTEST` (missing: `year_founded`). D's year < founded year → `BEFORE_FOUNDING`. Otherwise attested, value = founded year. |
| `listing` | `revenue.public_markets.ipo_date` ≤ D → attested "listed", with the IPO date as point date. Later or null → cannot attest. Never assert "not listed". |
| `revenue_band` | Latest `revenue.estimated.timeseries` point ≤ D, with the same staleness rule; value = the bounds. Label "estimate". |
| `domains` | `basic_info.all_domains`, label "true at retrieval only". This is current-only, never historical. |
| anything else | `NO_RECORD_TYPE`. |

Applies to every field:
- D > T (retrieval) → `FUTURE_DATE`.
- Points dated after D go into `subsequent_events` and are never attested.
- Every `statement` uses the template in config: *"Data point dated P states X; stored copy retrieved T."* **Never write "was true on D".**
- A malformed or missing record, or a source error → `SOURCE_UNAVAILABLE`, never an answer.

**Audit verdicts (`audit_claims`):**
- `agree` / `contradict` only when the claim's date is within `contradict_date_window_days` of an attested point.
- `contradict` only when the gap exceeds `contradict_tolerance_pct`.
- Otherwise `cannot_verify`.
- Growth or ratio claims → `cannot_verify`, showing both dated values.

## 4. Resolution (module `backend/pipeline/`)
1. Free autocomplete, then company search to narrow candidates, then `company/identify` **by domain only**.
2. A name with more than one candidate and no domain → `CANNOT_RESOLVE`, listing the candidates (the live data has 25 for "Shree Balaji Logistics").
3. All domains in `all_domains` map to one `crustdata_company_id`, so one company under two names stays one record and is charged once.

## 5. Platform (module `backend/platform/`)
- **MCP server:** FastMCP over stdio (`mcp` Python SDK) exposing the tools in §2, plus a CLI (`python -m backend.cli ...`) with the same functions.
- **Crustdata client:** use the existing `backend/crust/` (17 tests: cache with live / record / replay, rate limiter, 429/402/403 handling, ledger, caps, resume). **Do not rewrite it; extend it.** Fix `CREDIT_TO_INR` to come from config (`usd_per_credit × inr_per_usd`).
- **Outbox and approvals:** `actions.execute(key, fn)` persists `ActionRecord{pending}` **before** the effect, runs it, marks it done, and appends `{"key":...}` to `state/effects.jsonl` (fsync). On restart, pending actions are reconciled and never blindly re-sent. Approvals transition state once, so a double click is safe. Sends go only to the sandbox webhook (env `SANDBOX_WEBHOOK_URL`); if that's unset, they're logged to `state/sandbox_outbox.jsonl`.
- **Run state:** persisted after every step (atomic temp file + rename). A restart resumes with zero new network calls and no double-counted credits. Torn files are detected.
- **Limits:** per-run credit cap and time limit from config. Hitting a limit gives `BUDGET_HELD`, a clean resumable state.
- **Ledger:** every Crustdata call and every model call is recorded, in credits and ₹. `cost` is shown in every `CaseFile`.
- **Watchers:**
  - create (held), `/test` (free), and poll runs, so no tunnel is needed;
  - alert dedupe key `sha(watch_id, company_id, field, signal_date)`, so a duplicate delivery is a no-op;
  - tag each watcher with its idempotency key at creation, to close the gap between creating it and saving its id.
- **Timeouts:** a timed-out source is retried with backoff, then marked `SOURCE_UNAVAILABLE`. Silence is never read as an answer.

## 6. Crustdata surface
- **Enabled on our key and used:** autocomplete (free), `company/search`, `company/identify` (0.2 per match, unmatched free), `company/enrich` (2 per record), `web/search/live` (1) plus `web/fetch` (cost unmeasured), watchers (create free, alert 5, `/test` free, runs free), `account/credits` and `account/endpoints` (free).
- **Disabled on our key:** all `/batch/*`, person contact enrich, employee reviews, social posts, the live professional-network searches.
- **Not used, by choice:** person data (minimal personal data), and `job/search` (our request body got a 400; fix it from the docs before using it).
- **Demo contrast:** the Crustdata MCP (`claude mcp add --transport http crustdata https://install.crustdata.com/mcp`).

## 7. Tests: the definition of done
- `tests/cases/hidden_test_cases.json` holds 17 cases with answers computed from the fixtures. **Every case except C17 must pass in replay mode.** C17 needs one approved live record-mode call first.
- Engine: a pass and a fail fixture for each field rule. The staleness boundary is tested at exactly 14 and 15 days. `subsequent_events` is never attested. The statement wording test fails if any output contains "was true on".
- Platform:
  - replay makes 0 network calls;
  - kill-restart with `council/chaos_kill.py` (5 rounds) means each action happens once;
  - a double approval gives one send;
  - resume makes 0 new calls;
  - a cap lowered mid-run → `BUDGET_HELD`;
  - a duplicate watcher alert is a no-op;
  - a torn state file doesn't crash the restart.
- End to end:
  - `clear_counterparty delhivery.com` in replay mode produces a `CaseFile` with cited evidence and its cost, in under 10 seconds;
  - the MCP server lists all tools and answers C01 through the MCP protocol.

## 8. Ethics (Robustness 20: safety part; Demo 15: "who it could get wrong")
- Company data only.
- Every refusal names what is missing.
- Small or new companies get an evidence request, never a rejection.
- STALE never suspends anything automatically.
- Estimates and profile-derived counts are always labelled.
- Everything that leaves the system is held for a person.

## 9. Business case (for the README and demo)
- **Buyers:** procurement or vendor-onboarding heads; diligence and credit teams at banks, NBFCs and funds; insurers and arbitrators for dispute files.
- **Price:** ₹600 per *cleared* file (estimate; back it with KYB vendor quotes), refusals at cost.
- **Measured cost:** about 3–4 credits ≈ ₹85–110 per file. Show it from the ledger.

## 10. Demo (2 minutes)
1. The raw Crustdata MCP picks a "Shree Balaji Logistics", while AsOf says CANNOT RESOLVE, 25 candidates, needs a domain. **Use a real recorded run.**
2. `clear_counterparty delhivery.com` produces five cited lines and the ledger shows ₹.
3. Move the date: TCI 2020 is attested (418, from the 2019-12-30 point), and TCI 2026-10-15 flips to STALE_DATA (38 days).
4. Approve issuing the file, kill the process mid-send, restart: it's sent exactly once.
5. Watcher `/test` fires and a line goes STALE.

## 11. Cut order
UI → web corroboration → `audit_claims` → revenue_band.
**Never cut:** resolve, attest, the case file, the outbox, the ledger, watcher `/test`, the hidden-case tests.
