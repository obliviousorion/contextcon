# Sourced — SPEC / AGENTS.md
AI hiring desk. Input: a role brief (plain English) + optional raw CVs/profile links →
sourced candidates → every career claim verified against the live record or marked
"can't verify" → lookalikes and duplicates flagged, never silently merged → ranked,
cited shortlist → outreach and rejection notices drafted (held for recruiter approval,
sent only to our own sandbox channel, never to a real person) → call booked once, exactly
once, even across a crash. Plus a held-out evaluation harness that is itself a rehearsal
for the organizers' hidden test set.

## Event-rule constraints baked into this design (do not relax these)
- **Keep agents in the room.** Per the Builder Handbook: "During the event, your agents
  talk to your own team and to us, rather than to real people outside it." `Outreach`/
  `RejectionNotice` "send" is a POST to our own sandbox webhook (Slack-style), never a real
  SMTP/LinkedIn send, through build day and the demo.
- **Payments:** none in this track. No payment provider needed.
- **Cutoff:** organizer hidden test cases use records dated after 1 Sept 2026; our own
  eval Set A uses a `cutoff_date` leakage guard (see Eval harness) for the same reason
  Raise did — so a shortlist hit is never just the model's memory of who got hired.

## Rules for coding agents
- Touch ONLY your module dir. `backend/models.py` and `frontend/lib/types.ts` are
  FROZEN after hour 1; propose changes in `NOTES.md`.
- All Crustdata calls go through `backend/crust/client.py`. Keys only from `.env`
  (`CRUST_KEY`, `ANTHROPIC_API_KEY`, `SANDBOX_WEBHOOK_URL`, `PUBLIC_URL`).
- Every user-visible claim MUST reference Evidence ids. Verification verdicts
  (confirmed / contradicted / unconfirmed) are decided by deterministic matching rules in
  Python first; the LLM only extracts structured claims from free text and explains a
  verdict in prose. The LLM never decides a verdict on its own.
- No candidate is ever silently merged with another. A name collision is a
  `DisambiguationGroup` until resolved by a secondary signal with its own evidence id.
- Run your module's acceptance tests before declaring done.

## Stack
Python 3.12, FastAPI, httpx (async), Pydantic v2, sse-starlette, Claude (tool-use / JSON
schema). Next.js App Router + Tailwind + shadcn/ui + EventSource. Disk JSON cache.
cloudflared tunnel. Sandbox webhook (Slack Incoming Webhook into our own channel) stands
in for "send email" and "book call" — see Event-rule constraints above. No external
calendar API: a `CallBooking` is a proposed slot + an idempotent "booked" state, not a
real calendar write.

## Module split
- **Agent A:** `backend/crust/` (client, cache, rate limiter, budget/ledger) +
  `backend/watch/` (watcher create/test, webhook → sandbox)
- **Agent B:** `backend/agent/` (brief parsing, candidate sourcing, enrichment, claim
  extraction, verification engine, disambiguation, company-context sanity checks, market
  comparables, ranking, outreach + rejection drafting, citation validator) +
  `backend/eval/`
- **Agent C:** `frontend/` built against `fixtures/run_demo.jsonl` (fake SSE stream)

## Crustdata (base `https://api.crustdata.com`; headers `authorization: Bearer $CRUST_KEY`,
`x-api-version: 2025-11-01`, `content-type: application/json`)
Filter grammar: `{"op":"and"|"or","conditions":[{field,type,value}|group]}`; types
`= != < > =< => in not_in (.)` — NEVER `>=`/`<=`. Always pass `fields`.

| Use | Endpoint | Notes |
|---|---|---|
| permissions | `GET /account/endpoints?status=disabled` | free; run at startup, log disabled endpoints |
| source candidates | `POST /person/search` | filters: `title`, `experience.employer`, `skills`, `education.schools.school`, `location`; ~0.03cr/result; 30 RPM |
| verify a candidate | `POST /person/enrich` | `{professional_network_profile_urls:[≤25], fields:["experience","education","skills"]}`; full career history with dates — the ground truth every CV claim is checked against |
| resolve a claimed employer | `POST /company/identify` | `{domains:[...]}` or `{names:[...]}`; 0.2cr per matched identifier, unmatched is free |
| sanity-check seniority claims | `POST /company/enrich` | `{crustdata_company_ids:[≤25], fields:["headcount","funding","basic_info"]}`; 2cr/record; 15 RPM. `headcount` history lets us check "I led a 50-person team" against the company's actual size on that date |
| build a target-company set from the brief | `POST /company/search` | `search:{query:<brief context>, mode:"hybrid"}` + filters (country, headcount, funding stage) |
| market calibration | `POST /job/search` | live postings for the same/similar title — benchmark the brief's title and comp band against what the market is actually hiring for right now |
| verify a claim Crustdata can't confirm | `POST /web/search/live` | `{query, sources:["news","web"]}`; 1cr; 10 RPM (bottleneck — budget for this) |
| pull the exact passage | `POST /web/fetch` | fetch the specific page a web-search hit pointed to; the citation must quote this, never the search snippet |
| re-engagement trigger | `POST /watch/person/...` or `/watch/company/search` | "a webhook when a person, company or job posting you watch changes" (handbook, Annexure C) — watch a good-but-declined candidate for their next job change; free `/test` endpoint fires a demo alert on demand |

Parse responses defensively (`.get` chains); save one raw sample per endpoint in
`fixtures/raw/` at 9AM, same discipline as the Raise export.

## Schemas (`backend/models.py`, mirrored in `types.ts`)
- `Evidence{id "E{n}", kind: company|person|job_posting|web|market, source_endpoint, url|None, title, excerpt (≤400 chars verbatim), fetched_at, raw_ref}`
- `Citation{evidence_id, quote|None}`
- `JobSpec{role_title, seniority_band, must_have_skills:list[str], nice_to_have_skills:list[str], location, remote_ok:bool, company_context:dict, comp_range_hint|None, raw_brief}`
- `CareerClaim{id, candidate_id, text, claim_type: title|employer|dates|education|achievement|skill, employer_name|None, start_date|None, end_date|None, source: "cv"|"profile_text"}`
- `VerificationVerdict{claim_id, status: confirmed|contradicted|unconfirmed, evidence_ids:list[str], reason}`
- `DisambiguationGroup{id, shared_name, member_profile_urls:list[str], resolved:bool, resolved_candidate_id|None, resolution_evidence_ids:list[str]}`
- `CompanySnapshot{company_id, name, headcount_at_date|None, funding_stage_at_date|None, evidence_id}`
- `MarketComparable{posting_title, company_name, location, posted_date, evidence_id}`
- `Candidate{id, name, profile_url|None, current_title, current_employer, raw_enrich_ref, claims:list[CareerClaim], verdicts:list[VerificationVerdict], disambiguation_group_id|None, verification_confidence:0-1}`
- `ScoreComponent{name, weight, normalized 0-1, rationale, evidence_ids}`
- `ShortlistEntry{candidate, total 0-100, components:list[ScoreComponent], verification_confidence, flags:list[str]}`
- `Claim{text, citations:list[Citation] (min 1)}`
- `Outreach{candidate_id, subject, body_claims:list[Claim], status: draft|approved|sent_sandbox, dropped_claims:int, idempotency_key}`
- `RejectionNotice{candidate_id, reason, status: draft|approved|sent_sandbox, idempotency_key}`
- `CallBooking{candidate_id, slot, status: proposed|approved|booked, idempotency_key}`
- `LedgerEntry{run_id, ts, call, endpoint_or_model, credits|tokens, cumulative}`
- `TraceEvent{run_id, ts, step, status: start|progress|done|error|cache_hit|held_for_approval, message, data|None}`
- `Run{run_id, brief:str, job_spec:JobSpec, candidates:list[Candidate], disambiguation_groups:list[DisambiguationGroup], shortlist:list[ShortlistEntry], outreach:dict[str,Outreach], rejections:dict[str,RejectionNotice], bookings:dict[str,CallBooking], evidence:dict[str,Evidence], ledger:list[LedgerEntry]}`

## API
`POST /api/runs {brief, cv_files?} → {run_id}` · `GET /api/runs/{id}/stream` (SSE
TraceEvent; final step="complete" data=Run) · `GET /api/runs/{id}` ·
`GET /api/evidence/{eid}?run=` · `POST /api/outreach/{run}/{candidate}/approve` ·
`POST /api/rejection/{run}/{candidate}/approve` ·
`POST /api/booking/{run}/{candidate}/approve` ·
`POST /api/watch {run_id, candidate_id} → creates watcher` ·
`POST /api/watch/{id}/test` · `POST /webhooks/crustdata → sandbox` · `GET /api/eval → EvalReport`

## Pipeline (emit TraceEvent at every step)
1. Parse brief (LLM, structured output) → `JobSpec`.
2. Optional: build a target-company set from brief context via `company/search`, for
   passive sourcing ("people who've worked at Series B+ fintechs in Bangalore").
3. Source candidates: `person/search` with filters derived from `JobSpec`; dedupe raw
   hits by profile URL.
4. **Disambiguation pass, before anything else touches a name:** group candidates by
   `(name, approximate seniority)`. A group with >1 distinct profile URL is a
   `DisambiguationGroup` — resolved only by a secondary signal (overlapping
   employer+dates, education match, a uniquely identifying profile URL in the
   brief/CV). Unresolved groups surface in the UI as "2 people share this name" and are
   never auto-merged or auto-picked.
5. Enrich each resolved candidate: `person/enrich` → full career history with dates,
   education, skills. This is the ground truth everything else checks against.
6. If a raw CV/profile text was supplied: extract `CareerClaim`s from it (LLM,
   structured). If none was supplied, the enrich record's own claims are what gets
   verified (this still catches implausible self-reported seniority via step 7).
7. **Verify each claim** (deterministic matcher first, LLM only narrates):
   - employer + dates present and overlapping in the enrich record → `confirmed`.
   - employer + dates present but contradict the record (gap, overlap impossible,
     title mismatch) → `contradicted`, cite the enrich record.
   - employer not in the enrich record: resolve it via `company/identify`
     (does it exist at all?) → if yes, try `web/search` + `web/fetch` for
     corroboration → if none found, `unconfirmed` ("can't verify"), never guessed.
8. **Company-context sanity check:** for scope/seniority claims ("led a 50-person
   team", "first engineer", "Series B company"), pull the claimed employer's
   `CompanySnapshot` (headcount/funding at the claimed date) via `company/enrich` and
   flag implausible claims (e.g. "led 50 people" at a company with 10 employees that
   year) as `contradicted` with the snapshot as evidence.
   See career-physics-addendum.md for extra checks, finer verdicts and data trap rules for steps 7 and 8.
9. Market calibration: `job/search` for comparable live postings → attach
   `MarketComparable`s to the `JobSpec` for the recruiter-facing comp/demand context,
   and as a sanity check that the brief's title maps to a real market term.
10. **Rank** (deterministic, weights shown in UI):
    - skill_match 30: overlap of must-have/nice-to-have skills with enrich record
    - verification_confidence 25: share of claims `confirmed` vs `contradicted` vs
      `unconfirmed` (a `contradicted` claim caps total score hard, not just a
      weighted average — see note below)
    - recency 20: months since last relevant role (≤6 →1, ≥36 →0)
    - seniority_fit 15: claimed band vs. company-sanity-checked band
    - location_fit 10: exact / same metro / remote-ok
    - **A single `contradicted` claim caps verification_confidence at 0.2 regardless
      of other components** — a lie about one fact should not be averaged away by
      good facts elsewhere.
11. Draft `Outreach` for the top N (LLM, citation-constrained, see prompt below) →
    status `draft`; held for recruiter approval.
12. Draft `RejectionNotice` for anyone with a `contradicted` claim or a clearly
    unqualified skill match → same draft → approval flow. Rejecting an applicant is
    listed as an irreversible action in the handbook's own rules — it gets the same
    gate as outreach, not a lighter one.
13. On approval, "send" = POST to the sandbox webhook, keyed by
    `idempotency_key = hash(candidate_id + action + content)` so a retry (including a
    retry after a crash) never resends.
14. Propose `CallBooking` slots for approved outreach; booking itself needs its own
    approval; booked state is idempotent per `(run_id, candidate_id)` — a restart
    mid-booking re-checks state before writing "booked" again.
15. Watcher: watch 3–5 "good match but didn't reply / declined" candidates for a job
    change (re-engagement signal); free `/test` fires a demo alert on demand.
16. Ledger: every Crustdata/model call logged with its cost; run aborts to a safe,
    resumable held state if the budget cap is hit mid-run, rather than guessing or
    silently truncating the candidate list.

## Prompt: outreach with citations
System: "You write a short, factual outreach note from a recruiter to a candidate. You
may ONLY state facts present in EVIDENCE. Output JSON
`{subject, body_claims:[{text, citations:[{evidence_id}]}]}`. Every claim cites ≥1
evidence id. Names, dates, employers and numbers must appear verbatim in a cited
excerpt. Reference the specific verified experience that matches the brief — never a
claim marked `unconfirmed` or `contradicted`. ≤5 claims, ≤35 words each. No flattery, no
invented traction, no guessed seniority."

## Prompt: CV claim extraction
System: "Extract every factual career claim from this text as structured JSON:
`{claims:[{text, claim_type, employer_name, start_date, end_date}]}`. One claim per
fact. Do not infer dates or employers that are not stated. If a date is a range,
extract both endpoints. If a claim is vague ('led a team'), extract it as-is — verification
decides whether it holds up, not extraction."

## Citation & verdict enforcement (`backend/agent/verify.py`)
- Reject any claim whose cited evidence id isn't in `run.evidence`.
- A claim's verdict is never decided by the LLM alone: the matcher compares structured
  fields (employer name normalized, date ranges, title) against the enrich record and
  the `CompanySnapshot`; the LLM only writes the `reason` string once the matcher has
  already decided `confirmed`/`contradicted`/`unconfirmed`.
- >30% of a candidate's claims `unconfirmed` → the candidate is still shown, not
  dropped, with `verification_confidence` penalized and a visible "mostly unverifiable"
  flag — "can't verify" is a result, not a reason to hide someone.
- URLs are resolved from `Evidence` ids, never generated by the LLM.

## Eval harness (`backend/eval/`) — two sets, neither cuttable
**Set A — shortlist quality.** `eval/cases.json["shortlist"]`:
`[{role_brief, company_domain, posting_date, actual_hire_profile_url}]` — real,
documented hires (public news/LinkedIn), gathered day-of the same way Raise gathered its
funding-round cases. For each: run the pipeline with `cutoff_date = posting_date`
(drop any Crustdata/web data dated on or after it — the same leakage guard Raise used)
and check whether `actual_hire_profile_url` lands in the top-k shortlist. Baseline:
keyword title+skill match with no verification or ranking logic. Report
`hit_at_5`/`hit_at_10` vs. baseline, honestly.

**Set B — verification accuracy (the centerpiece).** `eval/cases.json["verification"]`:
synthetic candidate profiles, each with exactly one planted condition mirroring the
organizers' own hard-case pattern: a duplicate/lookalike name, a contradicted
employer/date claim, an unconfirmable claim with no settling source, an implausible
seniority claim a company-headcount check should catch, and at least one clean
fully-corroborated profile that must NOT be flagged. Score: did the system assign the
correct verdict to the planted condition in each case? This set is a direct rehearsal
for the hidden test set described in the problem statement (duplicate record, lookalike
name, "cannot verify" as the correct answer) — treat it as such.

`EvalReport{set_a:{hit_at_5, hit_at_10, baseline_hit_at_10, cases:[...]}, set_b:{accuracy, cases:[{case_id, planted_condition, verdict_given, correct:bool}]}}`.
UI table + two headline numbers. Report honestly whatever the result is.

## Cache, credits, demo
- Key `sha256(path + canonical body)`; store `{request, response, status, ts}`.
  MODE: `live` (read-through) | `record` | `replay` (cache only, miss = error event,
  never network). Never cache non-2xx.
- Token buckets: `person/search` 30/min, `person/enrich` 15/min, `company/enrich` 15/min,
  `company/search` 30/min, `job/search` 30/min, `web/search` 10/min (the bottleneck —
  budget claim-verification calls accordingly), `watch` 10/min; retry 429/5xx backoff
  1, 2, 4s.
- Budget cap per run: 400 credits (est. run ≈ 150–250 for a 10-candidate brief with
  verification). UI shows running credits live, same as Raise.
- `DEMO=1`: SSE replays `fixtures/runs/{id}.jsonl` at 0.3× original delays. Hidden
  toggle: press "d".

## UI (one page)
Header: brief input (+ optional CV upload) + Run. Left: live agent trace, including a
visible "held for approval" state, not just "done". Center: ranked shortlist (score
bars, verification-confidence chip, disambiguation badge where unresolved, flags).
Drawer per candidate: every claim with its verdict and source chip, outreach draft with
`[n]` citation popovers + Approve, rejection draft + Approve where applicable, booking
slot + Approve. Tab: Eval (two headline numbers: shortlist hit-rate vs. baseline,
verification accuracy + per-case table). Tab: Watch (create + "send test alert").

## Acceptance tests
**A:** replay makes 0 network calls (respx); rate limiter spacing; filter serialization
(no `>=`/`<=`); webhook → sandbox mocked; budget cap halts a run cleanly and leaves it
resumable.
**B:** cutoff filter removes all data dated ≥ cutoff (leakage test); disambiguation
never auto-merges two distinct profile URLs; a single `contradicted` claim caps
`verification_confidence` at 0.2 on a fixture; citation validator rejects a fake evidence
id and an unsupported number; idempotency key prevents a double-send on a simulated
crash-and-retry; pipeline replay full `Run` < 10s; eval runs on fixtures for both sets.
**C:** fixture SSE renders trace including a "held for approval" state; shortlist table
sorts; drawer opens and shows verdict+source per claim; approval buttons transition
state once, not twice on a double-click; eval tab renders both sets; no console errors.

## Cut-lines
1 PM behind → drop market calibration (`job/search`) and watcher; keep
brief → source → disambiguate → enrich → verify → rank → outreach/rejection drafts →
approval → UI. 4:30 PM → feature freeze; if watcher is broken, POST a captured payload
to the sandbox webhook manually, same fallback Raise used. **Eval Set B is not
cuttable** — it is the single clearest proof that the system does what the rulebook
asks, and it is the cheapest thing in the build to keep (synthetic fixtures, no live
calls required to run it in replay mode).
