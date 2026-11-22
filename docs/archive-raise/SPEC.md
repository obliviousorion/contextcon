# Raise — SPEC / AGENTS.md
AI fundraising agent for founders. Input: startup (domain or one-liner) + target stage → peers → who actually led rounds → ranked, conflict-checked investors → right partner + warm-intro path → cited outreach drafts (held for approval) → watcher alerts to Slack. Plus a held-out evaluation harness.

## Rules for coding agents
- Touch ONLY your module dir. `backend/models.py` and `frontend/lib/types.ts` are FROZEN; propose changes in NOTES.md.
- All Crustdata calls go through `backend/crust/client.py`. Keys only from `.env` (CRUST_KEY, ANTHROPIC_API_KEY, SLACK_WEBHOOK_URL, PUBLIC_URL).
- Every user-visible claim MUST reference Evidence ids. Ranking is deterministic Python; the LLM only parses input and writes prose.
- Run your module's acceptance tests before declaring done.

## Stack
Python 3.12, FastAPI, httpx (async), Pydantic v2, sse-starlette, Claude (tool-use / JSON schema). Next.js App Router + Tailwind + shadcn/ui + EventSource. Disk JSON cache. cloudflared tunnel. Slack Incoming Webhook (or Crustdata native Slack notification if schema verified).

## Module split
- Agent A: `backend/crust/` (client, cache, rate limiter, budget) + `backend/watch/` (watcher create/test, webhook → Slack)
- Agent B: `backend/agent/` (startup resolve, peers, investor aggregation, ranking, conflicts, partners, intros, outreach, citations) + `backend/eval/`
- Agent C: `frontend/` built against `fixtures/run_demo.jsonl` (fake SSE stream)

## Crustdata (base https://api.crustdata.com; headers `authorization: Bearer $CRUST_KEY`, `x-api-version: 2025-11-01`, `content-type: application/json`)
Filter grammar: `{"op":"and"|"or","conditions":[{field,type,value}|group]}`; types `= != < > =< => in not_in (.)` — NEVER `>=`/`<=`. Always pass `fields`.
| Use | Endpoint | Notes |
|---|---|---|
| permissions | GET /account/endpoints?status=disabled | free; run at startup, log disabled endpoints |
| resolve startup | POST /company/identify or /company/enrich {domains:[...]} | |
| peers | POST /company/search | `search:{query:<one-liner>,mode:"hybrid"}` + filters (country, year_founded, headcount); limit 40; ~0.03cr/result + premium groups |
| enrich | POST /company/enrich | `{crustdata_company_ids:[≤25], fields:["basic_info","headcount","funding","people","news","competitors"]}`; 2cr/record; 15 RPM. Key paths: `funding.milestones[]{date,amount_usd,round_type,investors,lead_investors}`, `funding.investors_detailed`, `people.founders[]`, `competitors`, `news[].article_url` |
| investor-backed search (optional) | POST /company/search with `funding.investors` filter | to find more portfolio companies of a candidate investor |
| partners | POST /person/search | current employer = investor firm, title contains partner/principal; UNVERIFIED field names → check autocomplete |
| intro paths | POST /person/enrich | `{professional_network_profile_urls:[≤25], fields:["experience","education"]}`; `experience.employment_details.past[]` |
| news | POST /web/search/live | `{query, sources:["news"], start_date}` unix s; 1cr; 10 RPM (bottleneck) |
| watcher | POST /watch/company/search | `{filters, config:{trigger:{type:"interval",every_hours:24},max_results_per_run:25}, notifications:[{type:"webhook",url}]}`; demo via FREE `POST /watch/company/search/{id}/test`; payload `{metadata, results.added[]}` |
Parse responses defensively (`.get` chains); save one raw sample per endpoint in `fixtures/raw/` at 9AM.

## Schemas (backend/models.py, mirrored in types.ts)
- Evidence{id "E{n}", kind: company|funding_round|person|news|web|competitor, source_endpoint, url|None, title, excerpt (≤400 chars verbatim), fetched_at, raw_ref (cache key)}
- Citation{evidence_id, quote|None}
- Round{company_id, company_name, date, round_type, amount_usd|None, lead_investors:list[str], investors:list[str], evidence_id}
- Investor{name, normalized_name, rounds_led:list[Round], rounds_participated:list[Round], stages:list[str], geos:list[str], last_active:date|None}
- Partner{name, title, profile_url, firm, evidence_ids}
- IntroPath{founder_name, partner_name, overlap_company, overlap_years:str, evidence_ids}
- ScoreComponent{name, weight, normalized 0-1, rationale, evidence_ids}
- InvestorScore{investor, total 0-100, components, conflict:Conflict|None, partners:list[Partner], intro_paths:list[IntroPath]}
- Conflict{competitor_name, round:Round, severity: exclude|flag, evidence_id}
- Claim{text, citations:list[Citation] (min 1)}
- Outreach{investor, partner|None, subject, body_claims:list[Claim], status: draft|approved, dropped_claims:int}
- TraceEvent{run_id, ts, step, status: start|progress|done|error|cache_hit, message, data|None}
- Run{run_id, startup:dict, stage, cutoff_date|None, peers:list[dict], rounds:list[Round], ranking:list[InvestorScore], outreach:dict[str,Outreach], evidence:dict[str,Evidence]}

## API
POST /api/runs {startup, stage, cutoff_date?} → {run_id} · GET /api/runs/{id}/stream (SSE TraceEvent; final step="complete" data=Run) · GET /api/runs/{id} · GET /api/evidence/{eid}?run= · POST /api/outreach/{run}/{investor}/approve · POST /api/watch {run_id} → creates watcher on peer filters · POST /api/watch/{id}/test · POST /webhooks/crustdata → Slack · GET /api/eval → EvalReport

## Pipeline (emit TraceEvent at every step)
1. resolve startup → enrich it (description, competitors, founders, country, stage).
2. peers = competitors ∪ company/search(hybrid query from description + filters: same country/region optional, year_founded ≥ startup−5) → top 40.
3. enrich peers in batches of 25 → extract Rounds; register each round as Evidence.
4. **cutoff filter:** if cutoff_date set, drop ALL rounds with date ≥ cutoff (eval leakage guard; also drop the startup's own rounds ≥ cutoff).
5. aggregate Investors (normalize names: lowercase, strip "ventures/capital/partners/llc/fund", alias map).
6. rank (deterministic, weights shown in UI):
   - relevance 30: # peer rounds led (log-scaled, cap 5)
   - stage_fit 25: led rounds of target stage ±1
   - recency 20: months since last lead in set (≤6 →1, ≥36 →0)
   - geo_fit 10: share of rounds in startup's country/region
   - participation 10: non-lead participations (log-scaled)
   - momentum 5: news in last 90d (only top 15, web search)
   Missing data → 0.5×weight, flagged "no data".
7. conflicts: investor led/participated in a round of a *direct competitor* (startup's `competitors` list) within 36 months → flag (exclude toggle in UI).
8. top 10 investors → partners via person/search (≤3 each) → person/enrich partners + startup founders → IntroPath where same past employer with overlapping dates.
9. outreach for top 5 (LLM) → citation validator → status draft; approve button.

## Prompt: outreach with citations
System: "You write a short cold email from a founder to an investor partner. You may ONLY state facts present in EVIDENCE. Output JSON {subject, body_claims:[{text, citations:[{evidence_id}]}]}. Every claim cites ≥1 evidence id. Numbers/dates/company names must appear verbatim in a cited excerpt. Mention why this investor fits (rounds they led in the space) and the intro path if present. ≤6 claims, ≤35 words each. No flattery, no invented traction."

## Citation enforcement (backend/agent/citations.py)
Reject claim if an evidence_id isn't in run.evidence; extract numbers (`\d[\d,.]*[%kKmMbB]?`) and capitalized entity tokens — each must appear (normalized) in a cited excerpt, else drop. >30% dropped → one retry with errors; then render survivors; show `dropped_claims`. URLs are resolved from Evidence ids, never generated by the LLM.

## Eval harness (backend/eval/)
- `eval/cases.json`: [{startup_domain, round_date, round_type, actual_leads:[...]}] — 10 cases; only keep cases where Crustdata's own milestone lists a lead.
- For each: run pipeline with `cutoff_date = round_date` and stage = round_type; hit@k if any normalized actual lead ∈ top k (k=10,20).
- Baseline: rank investors by total leads across all peer rounds ignoring stage/recency/geo (and a second baseline: global most-active investors in the cached set).
- Output EvalReport{cases:[{startup, actual_leads, rank_of_actual|None}], hit_at_10, hit_at_20, baseline_hit_at_20}. UI table + one headline number. Report honestly whatever the result is.

## Cache, credits, demo
- Key sha256(path + canonical body); store {request, response, status, ts}. MODE: live (read-through) | record | replay (cache only, miss = error event, never network). Never cache non-2xx.
- Token buckets: enrich 15/min, person 15/min, search 30/min, web 10/min, watch 10/min; retry 429/5xx backoff 1,2,4s.
- Budget cap per run: 400 credits (est. run ≈ 150–250). UI shows running credits.
- DEMO=1: SSE replays `fixtures/runs/{id}.jsonl` at 0.3× original delays. Hidden toggle: press "d".

## UI (one page)
Header: startup input + stage select + Run. Left: live agent trace. Center: ranked investor table (score bars, stage chips, conflict badge, "led N rounds in your space"). Drawer per investor: rounds with source chips, partners, intro paths, outreach draft with [n] citation popovers + Approve. Tab: Eval (headline hit@20 vs baseline + per-case table). Tab: Watch (create + "send test alert").

## Acceptance tests
A: replay makes 0 network calls (respx); rate limiter spacing; filter serialization (no >=/<=); webhook → Slack mocked.
B: cutoff filter removes all rounds ≥ cutoff (leakage test); name normalization merges aliases; ranking deterministic; conflict detection on fixture; citation validator rejects fake id & unsupported number; pipeline replay full Run < 10s; eval runs on fixtures.
C: fixture SSE renders trace, table sorts, drawer opens, citation popover shows URL, eval tab renders, no console errors.

## Cut-lines
1 PM behind → drop intro paths + watcher; keep peers→rounds→ranking→conflicts→outreach→UI. 4:30 PM → feature freeze; if watcher broken, POST a captured payload to the webhook manually. Eval is NOT cuttable — it's the centerpiece; shrink to 5 cases if needed.
