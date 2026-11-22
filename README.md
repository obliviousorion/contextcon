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

**What a strong idea also needs to show (Handbook, "What we want to hear" and "How the finals run"):**
- The business case: who buys it, the price in rupees, and what one job costs to run.
- An answer to the scale question: "100 times the volume, or a second client?"
- Handling beyond the prepared request: a duplicate record, a changed fact, a failed call, or a restart mid-run.
- The approaches weighed, the hardest case, and who the product could get wrong and how it guards against that.

**What changed from earlier assumptions.** The ideas below were first scored against the separate `ContextCon05_BITS_Problem_Statement.pdf`, whose rubric was ethics 25, finance 25, live run 20, robustness 15 and design 15. It also framed every idea around a fictional Indian 3PL client. **The Handbook uses the rubric above and doesn't require the 3PL framing.** That framing is now optional, so ideas dropped only for not serving the 3PL client, such as Raise, may deserve another look. The council scores in the leaderboard use the old rubric; see the note under the table.

---

## Leaderboard

**Rank order:** first by the **Round 3 score (/100)**, which uses the Handbook rubric and is the current source of truth. Ideas without a Round 3 score are ordered by Round 2 wins, then by Round 1 score.
- **Round 3:** three judges score each Handbook criterion 1–5, scaled by its weight: E2E 25 · Facts 20 · Robustness 20 · Value 20 · Demo 15. Reviews are in [`ideas/_council/reviews/`](ideas/_council/reviews/).
- **Rounds 1 and 2** used the problem statement's older rubric. Round 1 is five judges scoring 1–5, maximum 25. Round 2 is head-to-head matchups between four finalists, nine each.

| Rank | Idea | One line | **Round 3 /100** (E2E·Facts·Rob·Value·Demo) | Round 2 wins /9 | Round 1 /25 | Status | Doc |
|---|---|---|---|---|---|---|---|
| 🥇 1 | **AsOf** | Dated attestation. It states what the records can prove as of date D, or says CANNOT ATTEST. Delivered as an MCP gateway | **88** (4·5·5·4·4) | **8** | **22** | **Champion (merge)** | [01-asof.md](ideas/01-asof.md) |
| 🥈 2 | **Golden Record** | Entity resolution: merge / no-merge / cannot verify for each pair; one company under two names stays one record | **73** (4·4·4·3·3) | — | 19 | AsOf's resolution step | [05-golden-record.md](ideas/05-golden-record.md) |
| 🥉 3 | **Second Opinion** | Audits a deliverable someone else produced, line by line (agree / contradict / cannot verify) | **71** (4·2·3·4·5) | 1 | 18 | Candidate front door for AsOf | [04-second-opinion.md](ideas/04-second-opinion.md) |
| 4 | FactGate | Verified-facts MCP gateway: a sourced value or CANNOT_VERIFY | 68 (3·4·4·3·3) | 7 | 21 | Absorbed into AsOf | [02-factgate.md](ideas/02-factgate.md) |
| 5 | Sentinel | "Evidence that you knew": watchers turn counterparty changes into dated records | 60 (3·3·3·3·3) | 2 | 18 / 16 / 16 | Watcher design absorbed | [03-sentinel.md](ideas/03-sentinel.md) |
| 6 | Raise | Fundraising agent for founders (re-scored now that the 3PL framing is optional) | 56 (3·2·3·3·3) | — | not scored | Dropped (a ranking has no checkable answer) | [17-raise.md](ideas/17-raise.md) |
| 7 | Same Hands | Related-party graph across tender bidders | 55 (3·2·2·3·4) | — | 15 | Dropped (defamation risk) | [08-same-hands.md](ideas/08-same-hands.md) |
| 8 | Carrier Pulse | Carrier distress watchlist (red / amber / green) | — | — | 16 | Merged into Sentinel | [06-carrier-pulse.md](ideas/06-carrier-pulse.md) |
| 9 | LaneWatch | Dated hold / continue verdict on carrier health | — | — | 16 | Merged into Sentinel | [07-lanewatch.md](ideas/07-lanewatch.md) |
| 10 | BudgetBroker | Budget-governed data buyer (a proxy with a spending cap) | — | — | 15 | Possible AsOf feature | [09-budgetbroker.md](ideas/09-budgetbroker.md) |
| 11 | Bid Intel | Rival dossier before a tender | — | — | 14 | Dropped (track example) | [10-bid-intel.md](ideas/10-bid-intel.md) |
| 12 | Expansion Site Scout | Hiring as a warehouse-demand signal | — | — | 13 | Dropped (job-search coverage) | [11-expansion-site-scout.md](ideas/11-expansion-site-scout.md) |
| 13 | ProvenanceAudit | Claim-by-claim auditor for agent memos | — | — | 13 | Dropped (track example) | [12-provenance-audit.md](ideas/12-provenance-audit.md) |
| 14 | Account Watch | Customer churn and expansion watch | — | — | 11 | Dropped (surveillance) | [13-account-watch.md](ideas/13-account-watch.md) |
| 15 | Notice-Period Alert | Flags when a named contact at a counterparty has left | — | — | 11 | Dropped (tracks individuals) | [14-notice-period-alert.md](ideas/14-notice-period-alert.md) |
| 16 | Conflict-of-Interest Desk | Screens bidders' directors for conflicts | — | — | 11 | Dropped (personal data, namesakes) | [15-conflict-of-interest.md](ideas/15-conflict-of-interest.md) |
| 17 | Sourced | Hiring desk with CV-claim verification | — | — | not scored | Dropped (hiring is an overdone track example) | [16-sourced.md](ideas/16-sourced.md) |

**Notes**
- The three Round 1 scores in Sentinel's row are Receivables Sentinel, Carrier Pulse and LaneWatch.
- Document file numbers are permanent IDs, not ranks.
- All rupee fee figures are agent estimates unless marked as sourced.

> **What Round 3 changed**
> - AsOf stays far ahead: 88, the only idea scoring 5 on Facts and on Robustness.
> - Golden Record and Second Opinion move into the top 3, because the Handbook weights a finished, checkable result and the demo, and drops the separate finance score.
> - Both new top-3 ideas are parts of AsOf: Golden Record is its resolution step, and Second Opinion is a possible way to present it.
> - Second Opinion's Facts score of 2 is a warning: its pitch marked a growth claim AGREE from two lower-bound counts.
> - Raise, re-scored without the 3PL constraint, comes 6th, because a ranking has no single correct answer.

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

**Round 3 findings (Handbook rubric, 88/100):**
- **Facts 5 and Robustness 5.** The facts judge confirmed every case number against the recorded data, including the 14-day staleness refusal for TCI on 2026-10-15.
- **Biggest wrong-fact risk:** a 2026 stored copy read as proof of what was true on date D. **Fix:** word every line as *"data point dated P states X; stored copy retrieved T"* and never as "was true on D".
- **Biggest E2E risk:** requests outside basic info, headcount and revenue fall to web corroboration and may end as a "finished refusal". Mitigation: choose request types the data can actually settle.
- **Best buyers without the 3PL framing:**
  - insurers and arbitrators who need "what was knowable on date D"
  - diligence and credit teams at banks, NBFCs and funds that already pay outside diligence firms
- **Option the value judge suggests:** use Second Opinion's graded diff as AsOf's front door. The pitch: "We re-check every line of the report you paid for, as of the date you relied on it."

Full spec: **[ideas/01-asof.md](ideas/01-asof.md)**

---

## 🥈 2. Golden Record — entity resolution (AsOf's resolution step)

**What it is:** dedupe and entity resolution for a firm's customer and carrier master data. Every pair of records gets an explicit **merge / no-merge / cannot verify** verdict with cited evidence (identify by domain, `all_domains`, founding year, office addresses), and is never silently merged. Merges into a master record are irreversible, so they wait for approval and are idempotent on a pair hash.

**Why it scored 73 in Round 3:**
- E2E 4, Facts 4, Robustness 4: the verdicts have crisp, testable answers.
- It hits the Handbook line "one person or company under two names stays one record" directly.
- Our data shows the problem is real: one name returned **25 candidates**, and Delhivery has two domains (`drl.aero`, `delhivery.com`).
- Value and Demo are only 3: "a real job but a low price; dedupe demo is dry".

**Weaknesses:**
- It fails on its own economics: about ₹53 of enrichment per record against a ₹5–20 price per record.
- The spec is thin, and the reasons for merging aren't yet sourced.

**Role in the champion:** AsOf's `resolve` step (domain or ID, never name).

Full doc: [ideas/05-golden-record.md](ideas/05-golden-record.md)

---

## 🥉 3. Second Opinion — audit someone else's report (possible front door for AsOf)

**What it is:** it re-verifies a deliverable another party handed you, line by line, and returns **agree / contradict / cannot verify** with exact passages and record dates. The deliverable could be a carrier's capability deck, a vendor's KYB pack, a rival's memo, or another AI agent's output. It audits the auditor.

**Why it scored 71 in Round 3:**
- Demo 5: "a graded diff reads instantly".
- Value 4: the buyer is a diligence or credit-risk team at a bank, NBFC or fund that already pays a diligence firm and wants an independent check.
- E2E 4: a finished audit report.

**Why it isn't higher:**
- **Facts 2.** Its pitch marked "TCI grew 4x" AGREE from the ratio of two lower-bound counts. That's a wrong fact.
- Its CONTRADICT threshold ("~30k vs 35,295") was arbitrary and not matched to the claim's date.
- Its LLM claim-splitter can split differently after a restart, which breaks exactly-once processing (Robustness 3).

**Fixes if we use it as AsOf's front door:**
- Take structured claims, with no live document splitter.
- Grade each claim with AsOf's `attest`.
- Show growth claims as two dated values side by side, never as a ratio.
- Only CONTRADICT when the claim's date matches the data point and the gap is outside the stated tolerance.

**Its 2-minute demo outline (value judge):**
1. A vendor's 10-line carrier pack goes in: "Check what we paid for."
2. The diff fills in live, Delhivery's two domains resolve to one record, and "Shree Balaji" comes back cannot verify with 25 candidates.
3. A judge kills the process mid-run; it restarts with no double charge, and a watcher alert marks a line STALE.
4. An approval gate sits before the contradiction report goes out, and the ledger shows about 5 credits per pack.

Full doc: [ideas/04-second-opinion.md](ideas/04-second-opinion.md). FactGate (now #4) and Sentinel (#5) keep their full write-ups in [02-factgate.md](ideas/02-factgate.md) and [03-sentinel.md](ideas/03-sentinel.md).

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
2. Do we keep the 3PL-client framing? It's optional under the Handbook. Without it, AsOf's buyer can be any firm that onboards counterparties, such as procurement, lending or insurance.
3. Who sources the finance numbers: KYB vendor quotes, the MCA21 fee schedule, and IRDAI surveyor fees?
4. Is it OK to spend about 1.5 credits verifying `drl.aero` and measuring the web-fetch cost?
5. Done: Round 3 re-scored the top ideas against the Handbook rubric (see the leaderboard). The new decision is whether AsOf leads with its own clearance or dispute file, or with Second Opinion's "audit the report you paid for" framing.

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
