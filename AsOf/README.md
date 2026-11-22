# AsOf

> Crustdata gives you raw data. AsOf decides what it can swear to, and as of when.

AsOf is a service (an MCP server plus a CLI) that returns a **case file** about a company. Every line either states what a dated record says, with its source, or says CANNOT ATTEST and names what is missing. It never guesses.

## The job, and who pays today
- **Clearance:** a firm onboarding a counterparty (a carrier, a borrower, a vendor) must show what is provably true about it. Today a procurement or vendor-onboarding team, or a KYB vendor, assembles a folder of screenshots and notes.
- **Dispute:** after a loss, an insurer or arbitrator asks what was knowable about the company on a past date D. Today that is also screenshots and guesses.
- **Buyers:** procurement and vendor-onboarding heads; diligence and credit teams at banks, NBFCs and funds; insurers and arbitrators.
- **Price: Rs 600 per cleared file. This is an ESTIMATE, not a quote.** It is not yet backed by KYB vendor quotes (IDfy, Signzy, Perfios/Karza) or a fee schedule. Refusals are billed at cost. Any dispute-file price is unsupported.

## Input and finished result
| Request (MCP tool = CLI command) | Input | Finished result |
|---|---|---|
| `clear_counterparty` (`clear`) | a domain | Clearance file as of today: five cited lines (existence, listing, headcount, revenue band, domains) plus cost |
| `dispute_file` (`dispute`) | domain, past date D | Dispute file as of D |
| `audit_claims` (`audit`) | domain, structured claims | Audit report: each claim agree / contradict / cannot verify |
| `request_evidence` | target, items | Held evidence request, labelled "Not a negative finding" |
| `resolve`, `attest`, `observe` | name or domain, field, dates | Resolution, one dated line, or two dated lines side by side (never a growth verdict) |
| `watch` | domain | A watcher; each alert re-attests today and marks lines STALE |

Every statement uses one template: "Data point dated P states X; stored copy retrieved T." It never says "was true on D". Estimates, "profile-derived count" and "true at retrieval only" are always labelled.

## Pass mark
- `uv run pytest -q`: **183 passed, 0 xfail** (2026-11-22).
- `tests/cases/hidden_test_cases.json`: 17 cases with answers computed from the recorded fixtures. All pass in replay, including C17.
- Engine: pass and fail fixtures per rule; staleness tested at exactly 14 and 15 days; a test fails if any output says "was true on".
- Chaos: `council/chaos_kill.py` kills the process 5 times at random moments; each action must happen once (see `docs/demo.md`).
- Council gate round 1535: all 5 reviewers PASS. That was before Phase 4 (the live record run); the later change (C17) is covered by the test suite, not by a new gate.

## Data sources and credit prices
Credits are Crustdata's unit. Prices below are measured unless marked.

| Endpoint | Credits | Used for |
|---|---|---|
| autocomplete | free | candidate names |
| `company/identify` (by domain) | 0.2 per match; unmatched free | binding a domain to one company |
| `company/enrich` | 2.0 per record | dated headcount, revenue estimate, listing, founding year |
| `/web/enrich/live` | 1.0 per page (balance dropped by exactly 1.0) | optional web corroboration |
| watcher create / `/test` / runs | free | watchers |
| watcher alert | 5 per alert | capped at 2 per company per month (config) |
| `account/credits`, `account/endpoints` | free | ledger reconciliation, permission check |

- `/web/fetch` returns 404 on our key. The working endpoint is `/web/enrich/live`.
- `company/search` is skipped: autocomplete plus identify-by-name already lists candidates.
- `job/search` is unused (our request body got a 400).
- Person endpoints are switched off. Company data only. Batch endpoints are disabled on our key.

## Where a person approves
Nothing leaves the system without a human. Held actions (config `approvals`): `issue_case_file`, `issue_audit_report`, `send_evidence_request`, `create_watcher`, `exceed_budget`.
- There is **no approve tool in MCP**. The agent can draft and ask to issue; approval is the CLI `approve <id>` by a person (recorded with name and time).
- `issue` on an unapproved item returns `held_for_approval`.
- Sends go only to the sandbox: `SANDBOX_WEBHOOK_URL` (https only), otherwise `state/sandbox_outbox.jsonl`.

## Ledger and measured cost per job
Every Crustdata call is written to a ledger in credits and rupees. Rate: 0.30 USD per credit x 94.12 INR per USD (OFX rate dated 2026-10-21, the latest dated rate found; in `config.yaml`) = Rs 28.24 per credit.

- **Measured: one clearance file = 2.2 credits = Rs 62.12** (identify 0.2 + enrich 2.0).
- In replay the file says: "Rs 0.00 spent this run (replay); Rs 62.12 measured cost of the stored copies (2.2 credits)".
- Live record run (user-approved, 2026-11-22): **7.8 credits** in total. Ledger: `fixtures/live_check/ledger/phase4-record-2026-11-22.jsonl`.
  - identify drl.aero: 0.2
  - `clear` delhivery.com, tciexpress.in, shreebalajigrp.com: 2.2 each (6.6)
  - one web page fetch: 1.0
- Margin on the estimated price: Rs 600 minus Rs 62.12 is Rs 537.88 (arithmetic on an estimated price). A web-corroborated file would add 1.0 credit per page (Rs 28.24).
- A watcher alert costs 5 credits (Rs 141.18 at the same rate); it is passed through at cost, not included in the file price.
- Limits: 40 credits per run and 300 seconds (config). Hitting a limit gives `BUDGET_HELD`, a clean resumable state.

## Run it from a fresh clone
Needs Python 3.12 and [uv](https://docs.astral.sh/uv/). Replay never touches the network and needs no key.
```bash
cd AsOf
uv sync
uv run pytest -q                      # 183 passed
export MODE=replay ASOF_TODAY=2026-11-22 ASOF_STATE_DIR="$(mktemp -d)"
uv run python -m backend.cli clear delhivery.com
```
Full 2-minute script: `docs/demo.md`. Design: `docs/architecture.md`.

Use it from Claude Code as an MCP server (stdio). Run this from the `AsOf` directory:
```bash
claude mcp add asof -e MODE=replay -e ASOF_TODAY=2026-11-22 -- uv run --directory "$PWD" python -m backend.platform.mcp_server
```
(The `claude mcp add` line was not run in this write-up; the server itself is tested over stdio in `tests/e2e/test_mcp_stdio.py`.) For the demo contrast, add Crustdata's own MCP: `claude mcp add --transport http crustdata https://install.crustdata.com/mcp`.

Never use `MODE=record` or `MODE=live` without the owner's approval: they spend credits.

## Approaches weighed
19 ideas were listed and the top ones scored by a council (see `../README.md` leaderboard). AsOf scored 88/100 on the Handbook rubric and won 8 of 9 head-to-head matchups. It is a merge:
- FactGate (a verified-facts gateway): its MCP delivery and "carrier cleared" lead job.
- Sentinel (watchers): the watcher design and the alert dedupe key.
- Second Opinion (claim audit, 71): a deterministic version, no LLM splitting.
- Golden Record (entity resolution, 73): the rule that one company under two names stays one record.
- Dropped: risk scores (no ground truth), growth verdicts from lower-bound counts, person-level ideas (personal data).

## What worked and what didn't
Worked:
- Pure engine functions over dated points. Thresholds live in `config.yaml`.
- Persisting intent before the effect: kill-restart tests pass.
- Replay: the full demo runs offline in about a second per command.

Didn't:
- `job/search` gave a 400; left unused.
- `/web/fetch` is a 404; `/web/enrich/live` works.
- The first recorded identify/enrich calls were batched, so replay needed a fallback index over the cache. The index also inferred drl.aero = Delhivery from `all_domains`, which was wrong. Phase 4 recorded one request per company and the index was deleted: replay now serves only exact recorded requests.
- Our first inferred answer for C17 was wrong (below).

## The hardest case: C17, drl.aero
Delhivery's record lists `drl.aero` in `all_domains`, so the build assumed drl.aero = Delhivery (id 5798). One live identify (0.2 credits) on drl.aero returned **two matches at confidence 1.0**: Delhivery (5798) and Delhivery Robotics (15944579, whose primary domain is drl.aero).

AsOf now returns `CANNOT_RESOLVE` ("a domain that matches exactly one company") with both candidates and an evidence request labelled "Not a negative finding". The resolver no longer treats an alias as proof: each new domain gets its own identify (0.2 credits). One company still stays one record: one Entity per `crustdata_company_id`, and the enrich record is charged once.

Lesson: an alias in a record is a claim, not proof. Guessing here would have attached Delhivery's file to a different company.

## Who it could get wrong, and the guards
- **A small or new company looks bad because the records are thin.** Thin records produce an evidence request ("Not a negative finding"), never a rejection. STALE never suspends anyone automatically.
- **A lookalike name or domain.** A name with more than one candidate and no domain gives CANNOT_RESOLVE. A domain matching two companies does the same (C17).
- **A stored copy read as proof of the past.** Lines say what a dated point states and when the copy was retrieved. Points after D go to `subsequent_events`, never attested.
- **Estimates read as facts.** Revenue is labelled "estimate", headcount "profile-derived count", domains "true at retrieval only".
- **A source error read as an answer.** Timeouts are retried with backoff, then `SOURCE_UNAVAILABLE`. Silence is never an answer.
- **A model or script acting alone.** Everything that leaves the system waits for a person; no MCP approve tool.
- **Personal data.** None: company records only.

## Webhook caveat (exactly-once has a window)
`actions.execute` writes the action as pending before the effect, runs it, marks it done, then appends the key to `state/effects.jsonl`. A kill after the send function returns but before that effects line is appended can make a restart run the send again. The receiver must therefore dedupe on `idempotency_key`, which every sandbox payload carries. Exactly-once is: at-most-once per key at the receiver, plus a small window on our side. The chaos test shows no duplicate keys in our log; it cannot prove what an external receiver saw.

## What's next
- Back the Rs 600 price with KYB vendor quotes and the MCA21 fee schedule.
- Fix `job/search` from the docs as an "operating activity" signal.
- A per-client key, cap and cache, and a queue in front of the 15-requests-a-minute enrich limit (batch endpoints are disabled on our key).
- A court and insolvency record source, so "will it default?" can be answered by something other than CANNOT ATTEST.
