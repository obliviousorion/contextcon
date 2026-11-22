# #16 — Sourced (hiring desk with CV-claim verification) — superseded

Back to the [leaderboard](../README.md). Not scored by the idea council (it predates it).

**Status:** chosen ~13:00, superseded at ~13:20 when the judges told the team the standard tracks (Hiring is one) are overbuilt. Its engineering carries over to AsOf.

## What it was
AI hiring desk for the 3PL client: a role brief becomes a verified, ranked shortlist; every CV line is checked against Crustdata person/company records with deterministic checks (job ends before it starts, starts before employer was founded, team size larger than the department, title-level mismatch, ...); verdicts confirmed / contradicted / unconfirmed with evidence grades; lookalike names kept as unresolved groups; held-for-approval outreach, "please clarify" (right of reply) and booking.

## Where the full material lives
- Teammates' spec + plan: [docs/sourced-spec/](../docs/sourced-spec/) (SPEC.md, sourced-winning-plan.md, agent prompts, cheatsheet, eval cases)
- Career-physics addendum (live-checked data facts and trap rules): [docs/sourced-spec/career-physics-addendum.md](../docs/sourced-spec/career-physics-addendum.md)
- Our v2 spec, frozen models, 4-agent split: local build repo `sourced/` (SPEC.md, backend/models.py) — not pushed
- Agent prompts for the v2 split: [docs/prompts/](../docs/prompts/)

## Why it was dropped
- Judges: Hiring is a standard track, other teams will build screeners.
- Heaviest personal-data load of any plan (ethics is 25 points).

## What carries over to AsOf
Crustdata client (cache record/replay, limiter, ledger, resume — 17 tests), the idempotent-action/outbox design, the cannot-verify discipline, the trap rules (company id not name, refresh-date checks), config-driven verdict mapping, the council + chaos harness in [docs/council/](../docs/council/).

## Discussion

- **Atishay6571, 2026-11-22 14:40 IST: proposal to score Sourced as "Career Check" (narrowed scope plus the Career physics addendum) instead of dropping it unscored.** Appended under RULES §4; the owner merges. Not scored yet: it needs a Round 3 review (RULES §5). Credits spent: 0.

  **Why it deserves a score**
  - The Handbook is now the source of truth (RULES §0). It lists "1.2 The Career Check: Every line of a CV checked against the record" as a theme, and names background-check firms, paid for each candidate they verify, as today's payer ([builder-handbook.txt](../docs/builder-handbook.txt), "1. Hiring"). The Handbook never says track examples are overdone. That rule comes from the event judges' spoken feedback ([README](../README.md), "Why we re-ideated").
  - The champion's lead job is a track example too. AsOf's `clear_carrier` ([01-asof.md](01-asof.md), line 31) is a vendor check, and vendor checks are on the same overdone list. It passed on its approach: as-of attestation and refusing to guess. Bid Intel and ProvenanceAudit were marked "track example" only after they were scored.
  - Proposal for every idea alike: judge uniqueness on the approach, which the Handbook asks for as "an approach that is not obvious" under Customer value and idea, through that scored criterion rather than as a gate before review.

  **The approach that isn't obvious** (from [career-physics-addendum.md](../docs/sourced-spec/career-physics-addendum.md)):
  - It separates lines that cannot be true from lines that are merely unproven. A job ending before it starts, or starting 2 or more years before the employer was founded, is impossible with no lookup of the person needed.
  - It grades the evidence: an independent record versus only the candidate's own profile.
  - "Implausible" goes to a person and never to a rejection. A contradicted line produces a held "please clarify" draft, which is the candidate's right of reply.
  - Verdicts never read name, gender, age or college.
  - Why other teams won't build it (our expectation): a typical Career Check matches the CV to a profile and stops. Joining each CV line to dated company records (founding year, headcount on that date) is the part most builds will skip.

  **Narrowed scope** ([sourced-winning-plan.md](../docs/sourced-spec/claude/sourced-winning-plan.md) §6, "Career Check only")
  - Input: one CV, plus an optional profile link. Output: one row per claim, with its verdict, the source field and the record's date.
  - Cut: sourcing through person search, ranking, market calibration and booking. Person enrich runs only for the candidate who applied, which answers "uses only the personal data the job needs".
  - Cost per CV (RULES §2 table): person enrich 1, plus company identify by domain 0.2 and company enrich 2 for each employer. Four employers ≈ 9.8 credits ≈ ₹255. Today's price per candidate is UNSOURCED; it needs a published Indian background-check rate card.

  **Rule gaps to close before review**
  - One person under two names stays one record (RULES §1): the spec never merges. Add a rule: merge only on a hard tie-breaker (the same profile URL, or the same employer with overlapping dates on both records); otherwise CANNOT VERIFY.
  - Record date: Evidence stores `fetched_at`, so each verdict must also show the record's own date. In practice that is the latest point in the time series ([round2-brief-and-data-check.md](_council/round2-brief-and-data-check.md), line 12).
  - A time limit on every run: only a credit cap exists.
  - A source that times out holds the claim for a person. It is never read as CANNOT VERIFY or as a pass.

  **Corrections the addendum needs (RULES §2)**
  - Its §4 says staff counts "miss drivers and warehouse staff". RULES §2 forbids claims about what headcount includes or excludes, and Sentinel was marked down for exactly this ([PROCESS.md](_council/PROCESS.md)). Say "profile-derived count" only.
  - Its §6 and Set B case 6 assume there are no staff counts before late Nov 2022. The live check found TCI Express data from 2019-10-28 ([round2-brief-and-data-check.md](_council/round2-brief-and-data-check.md), line 10). The rule should read: a team-size claim dated before the employer's first headcount point is CANNOT VERIFY.

  **If it doesn't place:** its checks fit AsOf's `audit_claims` as a request type for career claims.
