# Agent first prompts + pre-mortem (done 2026-11-22 morning)

Paste each prompt as the FIRST message in a fresh session in the repo root. SPEC.md must already be in the repo (copy from `claude/SPEC.md`). Freeze `backend/models.py` and `frontend/lib/types.ts` BEFORE starting A, B, C (9:00–9:45 task).

## Agent A: client / cache / watch (Claude Code, Sonnet, medium effort)
```
Read SPEC.md fully. You are Agent A. Touch ONLY backend/crust/ and backend/watch/ (plus tests for them). models.py is FROZEN; propose changes in NOTES.md.

Build, in this order, running tests after each:
1. backend/crust/client.py: async httpx client for base https://api.crustdata.com with headers authorization Bearer CRUST_KEY (from .env), x-api-version 2025-11-01. One method per endpoint in SPEC (permissions, identify/enrich, company search, person search, person enrich, web search live, watch create/test). Parse defensively (.get chains).
2. Cache: key sha256(path + canonical body), store {request, response, status, ts} on disk as JSON. MODE=live|record|replay. Replay never touches the network; a miss emits an error event. Never cache non-2xx.
3. Rate limiter token buckets: enrich 15/min, person 15/min, search 30/min, web 10/min, watch 10/min. Retry 429/5xx with backoff 1,2,4s.
4. Budget: per-run credit counter, cap 400, expose running total for the UI.
5. Filter builder: serialize {op, conditions:[{field,type,value}]}. Types allowed: = != < > =< => in not_in (.). NEVER emit >= or <=; raise if asked.
6. backend/watch/: create watcher (POST /watch/company/search with interval trigger + webhook), test endpoint, POST /webhooks/crustdata -> Slack incoming webhook (SLACK_WEBHOOK_URL).
7. Startup: call GET /account/endpoints?status=disabled and log disabled endpoints.

8. Robustness (judged at 20 points): honor 429 via the x-ratelimit-reset header before falling back to 1,2,4s backoff; treat 402 (out of credits) as a hard stop with a clear error event, never retry; 403 (disabled endpoint) returns a typed EndpointDisabled error the pipeline can skip; per-request timeouts; run state persisted to disk by run_id after every step so a crashed run can RESUME without re-spending credits (cache hits only); dedupe identical in-flight requests; idempotent webhook handling (same watcher payload twice posts to Slack once); never raise on a malformed or partial response, return a typed "unavailable" result instead.

Acceptance tests (pytest + respx): replay makes 0 network calls; limiter spacing; no >= or <= in serialized filters; webhook -> Slack mocked; 429 honors reset header; 402 stops without retry; 403 returns EndpointDisabled; resume-after-crash makes 0 new network calls; duplicate webhook posts once. Do not declare done until they pass. Keep answers short; list what you built and any SPEC deviations.
```

## Agent B: pipeline / ranking / eval (Claude Code, Opus or high effort for ranking + citations)
```
Read SPEC.md and eval-cases.md. You are Agent B. Touch ONLY backend/agent/ and backend/eval/ (plus tests). models.py is FROZEN. Use backend/crust/client.py only (Agent A is building it; until it lands, code against fixtures/raw/ responses via a small interface and do NOT call Crustdata directly).

Build in this order, test-first where the SPEC lists a test:
1. Pipeline steps 1-5: resolve startup, peers (competitors + hybrid search), enrich in batches of 25, extract Rounds as Evidence, CUTOFF FILTER (drop all rounds with date >= cutoff, including the startup's own rounds), name normalization with alias map.
2. Ranking (deterministic, weights exactly as SPEC: relevance 30, stage_fit 25, recency 20, geo_fit 10, participation 10, momentum 5; missing data = 0.5*weight flagged "no data"). Each ScoreComponent carries rationale + evidence_ids.
3. Conflicts (direct competitors, 36 months, flag with exclude toggle).
4. citations.py: reject unknown evidence ids; numbers and capitalized entities must appear in cited excerpts; drop failing claims; retry once if >30% dropped; track dropped_claims. URLs come from Evidence, never from the LLM.
5. Partners + intro paths + outreach (LLM JSON via tool use, prompt from SPEC).
6. backend/eval/: run cases with cutoff_date = round_date, stage = round_type; hit@10, hit@20, two baselines; EvalReport output. Co-leads count as a hit if either appears. Report honestly.

7. Robustness and "can't verify" (judged at 20 + 20 points): never guess. When data is missing (no lead on a round, no competitors, no partner found, person enrich fails) emit an explicit "unavailable: <reason>" state on that component or claim instead of inventing; a single failed peer, partner or enrich call must NOT abort the run (log an error TraceEvent, continue, report coverage like "31/40 peers enriched"); resume a crashed run from persisted step state; dedupe peers and investors across aliases; split lead_investors strings defensively on "," ";" and " and " and match case-insensitively; eval ground truth also strips parentheticals (e.g. "Peak XV Partners (Surge)" matches "Surge"); handle null dates and amounts; empty-input and unknown-domain startups return a clean error, not a stack trace.

Tests: leakage (no round >= cutoff survives), alias merge, ranking deterministic, conflict on fixture, validator rejects fake id and unsupported number, replay full Run < 10s, eval runs on fixtures, one failed peer does not abort the run, missing-lead round yields "unavailable", resume after crash, unknown domain returns a clean error. Use fixtures/raw/company_enrich_eval15.json as the realistic source. Emit TraceEvent at every step. Short answers.
```

## Agent C: frontend (Antigravity, separate quota)
```
Read SPEC.md (UI + API sections) and frontend/lib/types.ts (FROZEN). You are Agent C. Touch ONLY frontend/. Build against fixtures/run_demo.jsonl served as a fake SSE stream so you never wait on the backend; the real API is the one in SPEC.md, swap by env var.

Next.js App Router + Tailwind + shadcn/ui + EventSource. One page: header (startup input, stage select, Run); left live agent trace; center ranked investor table (score bars, stage chips, conflict badge, "led N rounds in your space", sortable, running credits shown); drawer per investor (rounds with source chips, partners, intro paths, outreach draft with [n] citation popovers that show the evidence URL + Approve button); Eval tab (headline hit@20 vs baseline + per-case table); Watch tab (create + "send test alert"). Hidden toggle: press "d" to switch DEMO replay.

First create fixtures/run_demo.jsonl yourself (a realistic fake TraceEvent stream ending with step "complete" data=Run) matching types.ts. Done when: fixture stream renders trace, table sorts, drawer opens, popover shows URL, eval tab renders, no console errors.
```

## Pre-mortem: "It's 9 PM and Raise lost. Why?"
Written by me inline (no subagents, to save usage). Ranked by likelihood x damage.

| # | Failure | Early warning | Prevention / mitigation |
|---|---|---|---|
| 1 | **`lead_investors` sparse or empty** in Crustdata for Seed/A rounds, so rankings are noise and the eval is meaningless | 9:00 spot-check: fewer than ~half of 15 eval companies have a lead on a milestone | Decide at 9:45. Fallback: Scout (plan section 7). Partial fix: treat press-named leads as ground truth only for eval; fall back to `investors` order or "participants" with a flagged lower weight |
| 2 | **Eval is bad** (Raise ≤ baseline) or leaks | hit@20 lower than baseline on first run; suspiciously high number | Never hide it. Show per-case table and say what it tells you. Run the leakage test first; show the cutoff filter code on stage. Shrink to 5-8 clean cases rather than tune on the test set |
| 3 | **Live demo breaks** (rate limits, 403 on a disabled endpoint, Wi-Fi) | any live run over 60s or any error during rehearsal | MODE=replay from recorded runs; hidden "d" toggle; 2.5 min backup video by 5:30 PM. Rehearse the replay path more than the live path |
| 4 | **Time runs out on integration** (three agents drift from models.py, merge conflicts) | at 12:00 the CLI doesn't print ranked investors | Frozen models, module dirs, 1 PM cut-line (drop intro paths + watcher), 4:30 feature freeze. Don't add features after 3 PM |
| 5 | **Credit/budget burn** (enrich is 2cr/record, 400cr cap) | credit counter climbs fast during eval | Cache everything, record once, replay for the rest. Eval peers can share the cache |
| 6 | **Judges see "database lookup"** | Q&A during rehearsal sounds weak | Lead with the reasoning chain + eval + conflict receipts. Have the cheat-sheet answers memorized (winning plan section 6) |
| 7 | **Hallucinated or unsupported claim shows up in demo** | validator drops >30% in rehearsal | Rules rank, LLM only parses/explains; show "N unsupported claims removed" as a feature. Pre-check the three demo startups' outputs by hand |
| 8 | **Pitch overruns / poor delivery** | rehearsal > 3:10 | 4 slides + live demo; time each rehearsal; cut the business slide to 20s if needed |
| 9 | **You hit the Claude usage limit mid-build** | window message in Claude Code | Follow the W1/W2/W3 plan in `on-hold-and-usage-plan.md`; C on Antigravity; fresh chat tomorrow; no subagents |
| 10 | **Hackathon rules** (prep code forbidden, "what did you build today" challenged) | n/a | Be exact: only SPEC + docs existed before 9 AM; start repo at 9:00 if rules require |

**Top 3 to act on first:** (1) the 9:00 `lead_investors` check, (2) leakage-safe eval before anything fancy, (3) record demo runs early so replay is always available.

## Slide deck
Built as a 4-slide Slides artifact "Raise: ContextCon Pitch Deck". Eval numbers on slide 3 are placeholders `[X/N]`, `[Y/N]`: fill them from the Eval tab. Pricing and the 2-8% figure are labeled estimates.
