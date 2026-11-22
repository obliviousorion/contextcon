# Benefits Desk

**An insurance desk for a company's own workforce, used by a licensed broker.** The employer side sees what similar employers promise and gets a cover package per staff group. Each opted-in employee learns what cover they hold, what is missing and what to do. When their records show a new employer, the desk states the date their old group cover ends and prepares the request to convert it. Nothing is bought or sent without the person's approval.

> This is a tool for a licensed insurance broker or agent. Comparing and advising on insurance for the public is regulated in India; the desk does not issue policies, set premiums or pay claims, and it never contacts anyone who has not opted in.

## The service
- **Who does this job today:** employee-benefits brokers and insurance advisers. **Who pays:** insurers, through the broker's commission on each policy placed (Builder Handbook, Insurance theme: "Brokers, through a commission on each policy they place"). The commission rate is not sourced here, so no rupee comparison is claimed.
- **Our price:** ₹150 per employee review and ₹1,500 per employer benchmark *(estimates, not sourced)*.
- **Measured cost per job** (from the ledger, ₹26.4 per credit; that rate is itself an estimate from RULES.md §2):

| Job | Credits | ₹ | Time (cold, record mode) |
|---|---|---|---|
| Employee review (person record 1.0 + job-post counts 0 + 2 quoted sample posts 0.06) | 1.06 | ≈ 28 | ≈ 6 s |
| Cover-gap alarm, direct request (person record) | 1.00 | ≈ 26 | < 2 s |
| Employer view with workplace beliefs (role counts 0, person-search counts + 2 × 10 leaver rows; measured across two runs) | 6.68 | ≈ 176 | ≈ 200 s (rate-limited) |
| Any repeat or resumed run | 0 | 0 | < 0.1 s |

Count-only job searches (`limit: 0`) cost nothing, which makes the employer benchmark almost free.

## What it does end to end (headless)
| Request | Finished result |
|---|---|
| `employee_review` | Fact file (Told / Checked / Guessed, each with its source field and date), cover gaps from `rules.yaml`, insurer shortlist on regulator figures, a pre-filled application **waiting for approval** |
| `job_change_check` | Cover-gap alarm: job-change date, old cover end date, conversion deadline, a conversion request **waiting for approval** |
| `peer_benchmark` | Count and share of peer job posts mentioning each cover phrase, with the filter JSON, the as-of time and quoted passages |
| `employer_package` | Package per staff group (drivers, warehouse, office) with the rule behind each item, peer counts by role, and versioned workplace beliefs |

Where it still needs a person: approving any send; answering the questions it raises (no public record, a told fact that conflicts with a checked one, which insurer when none can be ranked).

## How to run (fresh clone)
```bash
cd BenefitsDesk
uv sync
cp .env.example .env            # add CRUST_KEY only for record/live mode; replay needs no key
uv run python -m bd run requests/T2_peer_share.json          # replay: committed fixtures, 0 credits
uv run python -m bd run requests/T1_job_change.json
uv run python -m bd approve <key printed under Actions> --by person
uv run python -m bd sandbox &                                  # our own receiver; never a real insurer
uv run python -m bd act <run_id>                               # sends approved actions exactly once
uv run pytest -q                                               # 30 tests incl. the 20-trial kill test
# UI: cd web && npm install && npm run build && cd .. && uv run python -m bd serve   -> http://127.0.0.1:8787
```
Modes: `--mode replay` (default, `config.yaml`), `record` (calls Crustdata, caches every response), `live`. `--chaos` kills the process at random step boundaries.

## How it's built
```mermaid
flowchart LR
  REQ["Request JSON<br/>CLI / HTTP / UI"] --> RUN["Run: fixed step list per request type<br/>steps keyed by hash(run, step, inputs)"]
  RUN <--> SS[("SQLite step store<br/>finished steps skipped on restart")]
  RUN --> CL["Crustdata client<br/>cache by request hash · record/replay<br/>cap + time limit · backoff with jitter on 429/timeout"]
  CL -->|"hit: 0 credits"| CA[("response cache + committed fixtures")]
  CL -->|"/person/enrich · /job/search (count-only) · /person/search · /web/*"| CD[("Crustdata API")]
  CL --> LED[("Cost ledger: one row per call<br/>endpoint · credits · ₹ · cache hit · request hash, no personal data")]
  RUN --> FACTS["Facts = pointers (record, field path / char range)<br/>code copies the value; unresolved = CANNOT VERIFY"]
  RULES[["rules.yaml<br/>gaps · job change · package · ranking · phrases · group minimum"]] --> ENG
  FACTS --> ENG["Rules engine (pure)<br/>gaps · job-change alarm · package · insurer ranking"]
  BEL["Workplace beliefs (group only)<br/>versioned valid_from / valid_to"] --> CASE
  ENG --> CASE["Case file + report<br/>sections from config.yaml"]
  ENG --> INT["Intent log (idempotency key)"]
  INT -->|"person approves (CLI / UI)"| APP{"approved?"}
  APP -->|"sending → ask sandbox first on restart → done"| SB[("Sandbox receiver<br/>records every delivery")]
  LED -->|"cap or time reached"| HOLD["clean stop: settled vs missing"]
```
- **No language model in the core.** It is rules and lookups and gives the same answer every time, which is what the restart test needs, and it removes the main way a wrong fact gets in.
- **State:** `state/desk.sqlite` (steps, ledger, intents, personas, facts, beliefs, events) and `state/sandbox.sqlite`. Stdlib HTTP server; React + Vite + Tailwind UI in `web/`.
- **Every rule** lives in [`rules.yaml`](rules.yaml); **every limit and output field** in [`config.yaml`](config.yaml).

## Sources and checks
| Data | Source | What is cited |
|---|---|---|
| Employer, title, job dates | Crustdata `/person/enrich` (stored copy) | field path, entry date, retrieved time. The record has no refresh date, so "no change since" is always CANNOT VERIFY |
| Peer job posts | Crustdata `/job/search` | filter JSON, `total_count`, retrieved time; sample passages by `content.description[a:b]` and the post URL |
| Workplace beliefs | Crustdata `/person/search` | filter JSON per belief, `total_count`, window dates; leavers confirmed per row at that employer |
| Insurer figures | regulator page via `/web/enrich/live` (configured per figure) | quoted passage + URL + date, or CANNOT VERIFY |
| Age band, dependants, city, cover held, budget, insurer choice | the person | labelled **Told** |

**Approvals:** `submit_application` and `conversion_request` are irreversible, so they wait for `bd approve` (or the UI button). A double click is one action. Sends go only to our sandbox receiver.
**Ledger:** `uv run python -m bd ledger [run_id]`. Dev spend so far is in [`fixtures/DEV_LEDGER.md`](fixtures/DEV_LEDGER.md) (≈ 12 credits).

## Test cases (dated after 1 Sep 2026) and results
| Case | Correct answer | Result |
|---|---|---|
| **T1** opted-in persona, new employer after 1 Sep 2026 *(synthetic fixture: no consenting teammate has a job change)* | job change 2026-10-01 (Delhivery 5798 → TCI Express 5051), old cover ends 2026-09-01, conversion deadline 2026-10-01 already passed, conversion request awaiting approval | pass |
| **T1b** hard case: promotion in the same company | `same_company`: no alarm, no action | pass |
| **T2** share of logistics job posts in India since 1 Sep 2026 mentioning cover | 3,434 posts; health insurance 114 (3.3%), medical insurance 119, ESIC 17, mediclaim 3, accident cover 0; any phrase 246 (7.2%); filter + retrieved time | pass (live 22 Nov 2026) |
| **T3** person with no public record | CANNOT VERIFY employer facts, a question to the person, Told-only facts, 0 credits | pass (live) |
| **H1** duplicate sign-up (same profile, different URL form) | one persona (2 sign-ups), one action | pass |
| **H2** lookalike: name only, no profile link | refused: "a name alone can match several people; we never pick one" | pass |
| **H3** under 18 | stopped | pass |
| **E1** employer view, Delhivery · Gurugram | roles: drivers 16 posts (1 with cover), warehouse 39 (5), office 437 (29); joiners belief v1 20 (to 1 Oct), v2 9 (to 22 Nov) | pass (live) |

- **Kill test:** 20 trials under `--chaos` (kill probability 0.35 at every step boundary and inside the send), with approve clicked twice each time. Result: **82 kills, 20 deliveries, 0 duplicates.**
- **Requirement-change drill:** removing an output field and lowering the credit cap in `config.yaml` only (test).
- **Live-fix drill:** changing `R-GAP-6 budget_below` in `rules.yaml` changes the gaps, with no code change (test).

## Edge cases handled
Same-company role change (compares `crustdata_company_id`, not `recently_changed_jobs`) · several current jobs (`is_default`, else CANNOT VERIFY) · first-of-month dates (± 1 month) · leavers who left years ago (confirmed per row at that employer) · no refresh date (absence of change is CANNOT VERIFY) · name-only sign-up (refused) · duplicate sign-up (exact identifier only) · removed record (`match_status: redacted` → not processed) · no public record (ask; Told) · told vs checked conflict (show both, ask, no application) · group below the minimum (belief suppressed) · silent job post ("not mentioned") · missing insurer figure (CANNOT VERIFY, not ranked) · 429/timeout (backoff with jitter, then failed and not read as an answer; seen live) · cap/time reached (held before the call) · kill during a send (ask the sandbox before resending) · double approve · consent withdrawn (`bd forget`) · under 18 · personal data kept out of the ledger and logs.

## Approaches weighed
1. **A model that reads records and writes the advice:** fast to build, but it can state a fact that no record holds, and it can answer differently after a restart. Rejected for the core.
2. **Watches as the only trigger for the alarm:** watches fire at most hourly and a webhook can be missed across a kill. The **direct request** is the main path; the watch path pulls runs and shares the same rule function and action key.
3. **Rules plus pointers (chosen):** every outcome comes from a rule in one file, and every fact is a pointer that code resolves. Same answer every time, and a five-minute live fix is a YAML edit.

**What worked:**
- Count-only job search is free and exact.
- Step store and intent log survive kills.
- The 429 retry path was exercised by a real 429.

**What didn't:**
- Insurer regulator figures. Web search returned news pages and a redirect wrapper, not IRDAI's table, so every figure is CANNOT VERIFY and no insurer is ranked; the application goes to the person's own (Told) choice.
- `past.end_date` is not a filterable field, so leavers needed per-row checks.

**Hardest case:** a person whose record shows no change. Their record has no refresh date, so "nothing changed" cannot be verified. We say exactly that instead of "no alarm".

**Who it could get wrong:**
- Someone whose record is stale, so a real job change is missed. Guard: every "no change" says CANNOT VERIFY.
- A lookalike profile. Guard: a profile link is required, never a name.

## Not done (cut for time), and why not now
- **Live watch creation.** Crustdata needs a public notification URL and ours is local. `bd watch-create` refuses until `config.yaml watch.webhook_url` is set. The **pull path is built and tested**: `bd watch-pull <id>` reads finished runs after the last one processed, runs the same rule, prepares the same action key, and saves the run id. Direct and watch paths give the same alarm and one action (`tests/test_watch.py`).
- Insurer figures need IRDAI's own table URL per figure (`rules.yaml insurers.panel`).
- Monthly leavers on the timeline.
- Sourced broker commission for the price.

**100 times the volume:**
- Count-only benchmarks are free and shared across employees.
- Person records cost 1 credit each and are cached.
- The rate limit (30/min) is the ceiling, so batches queue behind the throttle.

**A second client:** a separate state dir and `rules.yaml` per broker. The rules file *is* the broker's policy.
