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
