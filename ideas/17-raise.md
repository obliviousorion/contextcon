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
