# ContextCon 05 — Ideas Leaderboard

Team workspace for ContextCon 05 (BITS Pilani × Crustdata × YC, Sun 22 Nov 2026). **We are not building yet: this page is for discussion.**
> **Adding or reviewing an idea? Give your agent [`ideas/RULES.md`](ideas/RULES.md) first.** New ideas start from [`ideas/_TEMPLATE.md`](ideas/_TEMPLATE.md), and reviews use [`ideas/_council/JUDGE_PROMPTS.md`](ideas/_council/JUDGE_PROMPTS.md).

Every idea has its own document in [`ideas/`](ideas/) with all the spec, data and council feedback gathered so far. How the ranking was produced is in [ideas/_council/PROCESS.md](ideas/_council/PROCESS.md). The old prep notes that used to be this README are now in [docs/PREP-NOTES.md](docs/PREP-NOTES.md).

**Why we re-ideated:** the event judges told us the standard track examples (hiring screeners, vendor checks, investor scouts, invoice matchers, ...) are what most teams build. We need a unique, out-of-the-box use of Crustdata's APIs, watchers and MCP. We also want to cover as much of Crustdata's API as is genuinely useful.

**Source of truth: the Builder Handbook, 39-page edition, [`docs/builder-handbook.pdf`](docs/builder-handbook.pdf)** ([text version](docs/builder-handbook.txt)). The older 34-page edition is in `docs/old/`.

**What we're judged on (Handbook, "How winners are picked").** Each criterion is scored 1–5, for 100 points in total. Ties go to end-to-end execution, then facts and verification.

| Criterion | Points | What the judges look for |
|---|---|---|
| End-to-end execution | **25** | A real request goes in and a finished result comes out (an offer drafted, a claim settled, an invoice paid, a case file written), with no one stepping in. The product asks a person only when the answer changes the result. |
| Facts and verification | **20** | Every person, company, number and date is right, **and right for the day it is used**. Each decision has reasons and sources. **One person or company under two names stays one record.** "I can't verify" beats a wrong fact. |
| Robustness and edge cases | **20** | It handles messy text, missing fields, unusual cases, and tools that time out or return nonsense. After a crash or retry it continues and never sends or pays twice. A person approves anything that can't be undone, and it uses only the personal data the job needs. |
| Customer value and idea | **20** | A job businesses pay people or firms to do today, with **an approach that isn't obvious**. The product does the work itself, not a chat interface on top of a model. |
| Demo and understanding | **15** | A clear demo, plus the approaches weighed, what worked and what didn't, the hardest case, who the product could get wrong, and what comes next. |

**What every service must do (Handbook, "What every service does"):**
- Decisions rest on live data.
- Every claim has a source that links to the exact passage or field, with the record's date.
- A person approves anything that can't be undone. Payments run in test mode.
- Every run has a time limit and a credit limit, and a ledger records every call, model calls included.
- It survives a crash or timeout and continues where it stopped, with each action happening exactly once.

**Test cases:** we gather our own before coding. They must include a duplicate record, a lookalike name, and a case where the right answer is "I can't verify", and be dated after 1 Sep 2026.

**Logistics:**
- Building runs 10:15–18:00. Code freeze at 18:00 is the one hard deadline.
- Submit a **public repo whose commit history starts at 10:15 on 22 Nov**, a 2-minute demo video, a public diagram link, and a declaration of "anything written before 10:15".
- Finals: **2 minutes of demo plus 1 minute of questions**. Be ready for "100 times the volume, or a second client?" and, if you can, show a duplicate record, a changed fact, a failed call or a restart mid-run.
- Judges want to hear the business case: who buys it, the price in rupees, and what one job costs to run.

**What changed from earlier assumptions.** The ideas below were first scored against the separate `ContextCon05_BITS_Problem_Statement.pdf`. Its rubric was ethics 25, finance 25, live run 20, robustness 15 and design 15, and it also described a fictional Indian 3PL client, a kickoff kit, an organizer repo, an hour-3 requirement change and a judge killing the process on stage. **The Handbook mentions none of these**, so treat them as unconfirmed. The council scores in the leaderboard use the old rubric; see the note under the table.

---

## Leaderboard

Round 1 is five judges scoring 1–5 each, maximum 25. Round 2 is three judges, each playing all six head-to-head matchups between the four finalists, so each finalist plays 9.

| Rank | Idea | One line | Round 1 /25 | Round 2 wins /9 | Status | Doc |
|---|---|---|---|---|---|---|
| 🥇 1 | **AsOf** | Dated carrier clearance and attestation. It states what the records can prove as of date D, or says CANNOT ATTEST. Delivered as an MCP gateway | **22** | **8** | **Champion (merge)** | [01-asof.md](ideas/01-asof.md) |
| 🥈 2 | **FactGate** | Verified-facts MCP gateway that every agent must pass facts through: a sourced value or CANNOT_VERIFY | 21 | 7 | Absorbed into AsOf | [02-factgate.md](ideas/02-factgate.md) |
| 🥉 3 | **Sentinel** | "Evidence that you knew": watchers turn counterparty changes into dated, sourced records | 18 / 16 / 16 | 2 | Watcher design absorbed into AsOf | [03-sentinel.md](ideas/03-sentinel.md) |
| 4 | Second Opinion | Audits another party's deliverable line by line (agree / contradict / cannot verify) | 18 | 1 | Light version absorbed | [04-second-opinion.md](ideas/04-second-opinion.md) |
| 5 | Golden Record | Master-data dedupe desk: merge / no-merge / cannot verify for each pair | 19 | — | Its entity resolution is in AsOf | [05-golden-record.md](ideas/05-golden-record.md) |
| 6 | Carrier Pulse | Carrier distress watchlist (red / amber / green) | 16 | — | Merged into Sentinel | [06-carrier-pulse.md](ideas/06-carrier-pulse.md) |
| 7 | LaneWatch | Dated hold / continue verdict on carrier health | 16 | — | Merged into Sentinel | [07-lanewatch.md](ideas/07-lanewatch.md) |
| 8 | Same Hands | Related-party graph across tender bidders | 15 | — | Dropped (defamation risk) | [08-same-hands.md](ideas/08-same-hands.md) |
| 9 | BudgetBroker | Budget-governed data buyer (a proxy with a spending cap) | 15 | — | Possible AsOf feature | [09-budgetbroker.md](ideas/09-budgetbroker.md) |
| 10 | Bid Intel | Rival dossier before a tender | 14 | — | Dropped (track example) | [10-bid-intel.md](ideas/10-bid-intel.md) |
| 11 | Expansion Site Scout | Hiring as a warehouse-demand signal | 13 | — | Dropped (job-search coverage) | [11-expansion-site-scout.md](ideas/11-expansion-site-scout.md) |
| 12 | ProvenanceAudit | Claim-by-claim auditor for agent memos | 13 | — | Dropped (track example) | [12-provenance-audit.md](ideas/12-provenance-audit.md) |
| 13 | Account Watch | Customer churn and expansion watch | 11 | — | Dropped (surveillance) | [13-account-watch.md](ideas/13-account-watch.md) |
| 14 | Notice-Period Alert | Flags when a named contact at a counterparty has left | 11 | — | Dropped (tracks individuals) | [14-notice-period-alert.md](ideas/14-notice-period-alert.md) |
| 15 | Conflict-of-Interest Desk | Screens bidders' directors for conflicts | 11 | — | Dropped (personal data, namesakes) | [15-conflict-of-interest.md](ideas/15-conflict-of-interest.md) |
| 16 | Sourced | Hiring desk with CV-claim verification | not scored — dropped on hard constraint (RULES §1: must be unique; hiring screeners are named as overdone) | — | **Dropped** | [16-sourced.md](ideas/16-sourced.md) |
| 17 | Raise | Fundraising agent for founders | not scored — dropped on hard constraint (RULES §1: must serve the one 3PL client; Raise serves founders) | — | **Dropped** | [17-raise.md](ideas/17-raise.md) |

The three Round 1 scores in Sentinel's row are Receivables Sentinel, Carrier Pulse and LaneWatch, the three ideas merged into it. All rupee fee figures are agent estimates unless marked as sourced.

> ⚠️ **These scores used the problem statement's rubric** (ethics 25 and finance 25), not the Handbook's. Under the Handbook, AsOf's core still lines up closely with *Facts and verification*: "right for the day it is used" and "one company under two names stays one record". *Customer value and idea* now rewards a non-obvious approach directly. A re-score against the Handbook rubric is pending; see open question 5.

---

## 🥇 1. AsOf — the champion

> **"Crustdata gives you raw data. AsOf decides what it can swear to, and as of when."**

**The problem**
A 3PL hands freight to many carriers, often small ones with near-identical names. Procurement has to know whether a carrier is real. After a cargo loss or SLA dispute, an insurer asks what the 3PL could have known about that carrier *on the date it picked it*.
- Raw data answers too eagerly. In our live check, the name "Shree Balaji Logistics" returned **25 candidate companies**, the top one at confidence 1.0.
- AsOf is the layer that refuses to guess.

**The service.** Each request is an MCP tool, a CLI command and a UI action.
- `resolve`: free autocomplete, then company search, then identify **by domain only**. Several candidates and no domain gives CANNOT RESOLVE.
- **`clear_carrier`**, the lead paid job: a clearance file showing existence, founding year, listing status, a profile-derived headcount point, a revenue band (labelled as an estimate), and corroborating dated web passages. Issuing the clearance waits for a person.
- `attest(entity, field, as_of=D)`: the core. It uses only the latest data point on or before D, which must be no more than 14 days old (configurable). Otherwise it answers CANNOT ATTEST and names what's missing.
- `observe(D1, D2)`: both dated values side by side. It never draws a growth verdict from lower-bound counts.
- `audit_claims`: grades structured claims, deterministically.
- `watch`: a Crustdata watcher. Each alert re-attests today, stores a hashed snapshot, and marks facts STALE.
- **Second product:** a dated dispute file for an insurer or arbitrator.

**Hidden-test cases.** Numbers are checked against our recorded data.
- Delhivery as of 2024-07-15: **26,656**.
- Delhivery headcount as of 2022-06-01: **CANNOT ATTEST**, because its series starts 2022-11-28.
- TCI Express as of 2020-01-01: **418**. As of 2026-09-01: **1,715**.
- Shree Balaji without a domain: **CANNOT RESOLVE**, 25 candidates.
- Any field outside the known record types: "CANNOT ATTEST: no record type".

**Crustdata used:**
- autocomplete, company search, identify and enrich (headcount series, revenue-estimate series, public markets)
- web search and fetch
- watchers (create, `/test`, runs)
- account credits and endpoints
- Crustdata's own MCP, as the demo contrast

Person data is deliberately not used.

**Ethics**
- Company data only.
- Refusals always name what's missing.
- Small carriers get a held "evidence request", labelled *not a negative finding*.
- No auto-rejection, and STALE never suspends a carrier.

**Finance**
- **Buyer:** the procurement head. **Price:** ₹600 per *cleared* carrier; refusals at cost or free.
- **Measured cost:** about ₹85–110 per file, so about 80% margin. Our ledger matched the Crustdata balance exactly.
- **Sources still needed:** published KYB vendor quotes (IDfy, Signzy, Perfios/Karza) and the MCA21 fee schedule.

**Robustness.** An outbox writes each action's intent before its effect, with an idempotency key, so actions run exactly once after a kill. Watcher alerts are deduped by `sha(watch_id, company_id, field, signal_date)`. Per-tenant keys answer the "second client" question.

**Demo moment.** The raw Crustdata MCP confidently picks the wrong Shree Balaji, and AsOf refuses. Then moving the date flips an answer to CANNOT ATTEST. Then a judge kills the process mid-send, and on restart it sends exactly once.

**Open risks**
- The kickoff kit's request format is unknown.
- Mostly refusals could make the demo look thin.
- The `drl.aero` alias and the web-fetch cost are unverified, about 1.5 credits to check.

Full spec: **[ideas/01-asof.md](ideas/01-asof.md)**

---

## 🥈 2. FactGate — runner-up, absorbed into AsOf

**What it is:** an MCP gateway in front of the 3PL's agents and staff. Every fact must pass through it and comes back with its field or passage, URL, record date and cost, or as CANNOT_VERIFY naming what's missing. The lead job is "clear a new carrier", about 4.2 credits (≈ ₹110), sold at ₹600 per dossier.

**What it adds to the champion:** MCP-gateway delivery, the carrier-clearance job (an example the problem statement itself gives), per-tenant caps, caches and audit logs, and watcher-driven fact expiry (STALE).

**What the judges said**
- The ethics and finance judge ranked it **#1**, because procurement already pays for KYB checks.
- The novelty judge scored it 3/5: "5+ teams will build fact-checkers".
- Flagged weak points: "cannot verify" quietly excludes small carriers, and no firm pays ₹600 for a refusal. The fixes (evidence requests, price per cleared dossier) are in AsOf.

Full doc: [ideas/02-factgate.md](ideas/02-factgate.md)

---

## 🥉 3. Sentinel — "Evidence that you knew"

**What it is:** a merge of Receivables Sentinel (a customer credit-hold desk for the CFO), Carrier Pulse and LaneWatch.
- Watchers on the 3PL's customers and carriers turn each change into a dated, sourced record, such as "headcount 18,626 on 2022-11-28 → 35,295 on 2026-11-16".
- There's no risk score. Credit holds and carrier suspensions stay human decisions.
- "Will X default?" is always cannot verify.
- About 8 credits (₹208) per alert-driven job.

**What it adds to the champion:** the watcher-centred design, and the alert dedupe key that closes the crash gap between creating a watcher and saving its ID.

**What the judges said**
- It had the best finance score in Round 1 (5/5).
- But CS and ethics objected: a verdict built on a headcount lower bound has no ground truth the organizers can test, and a false positive cuts a real customer's credit.
- It won 2 of 9 matchups in Round 2.

Full doc: [ideas/03-sentinel.md](ideas/03-sentinel.md)

---

## Live data check (14:00, 6.6 credits). Full detail in [round2-brief-and-data-check.md](ideas/_council/round2-brief-and-data-check.md)

**Resolution and history**
- Delhivery and TCI Express each resolve by domain to exactly one match.
- **"Shree Balaji Logistics" by name returns 25 candidates.**
- Delhivery has 204 weekly headcount points from Nov 2022.
- **TCI Express goes back to Oct 2019** (338 points).
- The small Shree Balaji has one point and no founding year.
- The weekly series have **gaps of up to about 5 months**, so AsOf needs its maximum-staleness rule.

**Endpoints**
- `job/search` returned a 400 because our request body was wrong. It cost 0.
- Autocomplete works and is free.
- 23 endpoints are disabled on our key: all batch endpoints, contact enrich, employee reviews, social posts, and the live professional-network searches.

**Ledger**
- The ledger total matched the account balance drop exactly.
- Recorded responses are cached in the local build repo (`sourced/fixtures/live_check/`) for free replay.

## Open questions for the team
1. Do we go with AsOf, and lead with **carrier clearance** (strongest buyer) or the **dated dispute file** (most novel)?
2. Do the kickoff kit and organizer repo exist? Only the problem statement mentions them. The Handbook says to submit our own new public repo and to gather our own test cases.
3. Who sources the finance numbers: KYB vendor quotes, the MCA21 fee schedule, and IRDAI surveyor fees?
4. Is it OK to spend about 1.5 credits verifying `drl.aero` and measuring the web-fetch cost?
5. Should we re-run the council against the **Handbook rubric** (E2E 25 · Facts 20 · Robustness 20 · Customer value 20 · Demo 15)? And do we drop the 3PL-client framing, which only the problem statement mentions?
6. The build code must go in a **new public repo with commits starting after 10:15**. The local `sourced/` repo has commits from 08:27, so it can't be the one we submit.

## Repo map
- `ideas/` holds one document per idea, plus `_council/` (the process, the Round 1 pool, the Round 2 brief and data check).
- `docs/` holds:
  - `PREP-NOTES.md` (the old README)
  - the builder handbook
  - `sourced-spec/` (teammates' Sourced spec and addendum)
  - `archive-raise/`
  - `prompts/` (agent prompts)
  - `council/` (council reviewers, chaos harness, gate)
- `check-key.sh` checks the Crustdata key.
- The local build repo `sourced/` is not pushed.
