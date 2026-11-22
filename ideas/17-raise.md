# #17 — Raise (fundraising agent for founders) — retired

Back to the [leaderboard](../README.md). Not scored by the idea council (it predates it).

**Status:** the original pre-event plan; retired ~12:30 after reading the organizers' problem statement.


## Round 3 (Handbook rubric) — 56/100
Scores E2E·Facts·Robustness·Value·Demo = 3·2·3·3·3 (each 1–5, weighted 25·20·20·20·15). Reviews: [_council/reviews/](_council/reviews/).

Re-scored without the 3PL constraint. A real request-to-held-drafts pipeline, but a ranking has no ground-truth answer; competitor lists were empty for 8 of 15 companies; it uses person data; it has no idempotent send.

## What it was
A founder enters a startup and target stage; Raise finds peers, pulls their funding rounds with named lead investors from Crustdata, ranks investors deterministically (relevance, stage fit, recency, geography), flags conflicts (investor backed a direct competitor), finds the right partner + warm-intro path, and drafts cited outreach held for approval. Centerpiece: a leakage-safe eval (hide a real round, check whether the actual lead lands in the top 20, vs a baseline).

## Evidence gathered
Live check at 08:35 (30 credits): `lead_investors` present for 15/15 eval companies, 14/15 matched ground truth (miss: "Surge" vs "Peak XV Partners (Surge)"); competitor lists empty for 8/15. Raw response: `sourced/fixtures/raw/company_enrich_sample15.json` (local repo).

## Why it was retired
- Every team serves one fictional Indian 3PL client; Raise serves founders, not that client.
- Hidden test cases need a "correct finished result"; a ranking has none.
- The real finals rubric (ethics 25, finance 25, kill-on-stage) differed from the one it was planned for.

## Full material
[docs/archive-raise/](../docs/archive-raise/) — SPEC, winning plan (council-reviewed), pre-mortem, API cheatsheet, eval cases.

## Discussion

- **Atishay6571, 2026-11-22 14:40 IST: proposal to give Raise a checkable answer, a verdict for each investor replayed from a past date.** Appended under RULES §4; the owner merges. Not scored yet: it needs a Round 3 review (RULES §5) before any leaderboard change. Credits spent: 0.

  **How it answers the Round 3 objections** ([R3-e2e-robustness.md](_council/reviews/R3-e2e-robustness.md), [R3-facts-verification.md](_council/reviews/R3-facts-verification.md)):

  | Round 3 objection | Proposed change |
  |---|---|
  | A ranking has no correct finished result | The output becomes a verdict for each investor (below). The order on screen is presentation only, and tests check the verdicts. The Handbook's own Investing ask is "calls replayed from a past date that match what happened next" ([builder-handbook.txt](../docs/builder-handbook.txt), "2. Investing"); the archived eval already replays with `cutoff_date`. |
  | Competitor lists were empty for 8 of 15 | Conflicts are checked only against rivals that have a record: rivals named in the request, plus Crustdata `competitors` when present. With neither, the conflict check answers CANNOT VERIFY ("no competitor list") instead of clearing the investor. |
  | Uses person data | Drop partner search and warm-intro paths (person search and person enrich). Company and funding data only. |
  | No exactly-once send | One outreach per approved investor, through an outbox keyed by `hash(run_id, investor_id, "outreach")`, sent only to our sandbox webhook. After a kill and restart, the outbox is read before anything is sent. |

  **Verdicts (deterministic rules, no model judgement):**
  - **ELIGIBLE:** led a round in the startup's peer set within 36 months before the cutoff, at the target stage or one stage either side. Cites the dated funding milestone.
  - **CONFLICTED:** led or joined a named rival's round within 36 months. Cites that milestone. Excluding an investor from a list is reversible, so it needs no approval.
  - **CANNOT VERIFY:** the milestone records no lead, the investor name can't be tied to one record, or there is no rival list. The answer names what is missing.

  **Alias rule** (Handbook: one person or company under two names stays one record). Investor names merge only on an explicit alias, such as "Peak XV Partners (Surge)" and "Surge". Looser matches stay separate and are shown as a possible duplicate. This is the miss the 08:35 live check found (see "Evidence gathered" above).

  **Test cases (draft):**

  | Request | Right result | Based on |
  |---|---|---|
  | Duplicate: one rival round led by "Peak XV Partners (Surge)", another by "Surge" | One investor record holding both rounds | live check 08:35 |
  | Lookalike: "Accel" and "Accel-KKR" both appear | Two records, never merged | assumption |
  | Can't verify: a peer milestone with an empty `lead_investors` | That round credits no investor; its lead shows CANNOT VERIFY | assumption |
  | Leakage: the startup's own round on the cutoff date | Dropped before any verdict; its lead isn't credited from it | archived SPEC, pipeline step 4 |
  | Replay: Raindrop, Series A, 2026-09-17, cut off that day | CRV appears as ELIGIBLE (a hit), or the miss is recorded | press lead in [cases-raise.json](../docs/archive-raise/cases-raise.json); Crustdata coverage UNVERIFIED |

  **Cost per job (RULES §2 table):** startup identify 0.2, plus peer search at 0.03 per result, plus company enrich at 2 per peer. 20 peers ≈ 40.8 credits ≈ ₹1,060. 40 peers ≈ 81.4 credits ≈ ₹2,120. Model calls are extra and not yet measured. Today's price: advisers take a success fee of 2–8% of the round (estimate, unsourced; the archived figure came from a seller of the service).

  **Why it's unique:** the track example is fund-side scouting ("2.1 The Pre-Round Scout: who raises next"). Raise works for the company that is raising, and its decision is conflict-checked eligibility, not who raises next. A Novelty judge may still call it adjacent, so the pitch should say so.

  **Optional 3PL framing:** the client is the one raising, and the rivals from its kickoff kit become the rival list. That also removes the empty-competitor problem.

  **Open risks:** lead-investor coverage for an arbitrary startup's peers is UNVERIFIED beyond the 15-company check. A raise is a one-off job, not a recurring one.
