# Crustdata API cheatsheet — Sourced

Base `https://api.crustdata.com`. Every call needs three headers:
```
authorization: Bearer YOUR_API_KEY
x-api-version: 2025-11-01
content-type: application/json
```
Filter grammar: `{"op":"and"|"or","conditions":[{field,type,value}|group]}`.
Types: `= != < > =< => in not_in (.)`. **Never** `>=` or `<=` — they silently fail.
Always pass `fields` on enrich/search calls; an unbounded `fields` list is slower and
costs more in premium groups.

## 0. Permissions (free, call first)
```
GET /account/endpoints?status=disabled
```
Log whatever is disabled on the hackathon key at 9:00 AM. If `person/enrich` or
`company/enrich` is disabled, the whole verification pipeline degrades to "sourced, not
verified" — that's the fallback in `agent-prompts-and-premortem.md`.

## 1. Source candidates — `POST /person/search`
```json
{
  "filters": {
    "op": "and",
    "conditions": [
      {"field": "title", "type": "=", "value": "Backend Engineer"},
      {"field": "experience.employer", "type": "in", "value": ["Series B fintech", "payments startup"]},
      {"field": "location", "type": "=", "value": "Bengaluru"}
    ]
  },
  "limit": 40,
  "fields": ["basic_info", "experience_summary", "skills"]
}
```
~0.03cr/result + premium field groups. 30 RPM. Loosen one filter at a time on zero
results; check exact field values with the Autocomplete API before retrying.

## 2. Verify a candidate — `POST /person/enrich`
```json
{
  "professional_network_profile_urls": ["https://linkedin.com/in/..."],
  "fields": ["experience", "education", "skills"]
}
```
15 RPM. `experience.employment_details.past[]` gives dated employer history — this is
the ground truth every `CareerClaim` is checked against. Batch ≤25 profile URLs per call.

## 3. Resolve a claimed employer — `POST /company/identify`
```json
{"domains": ["examplefintech.com"]}
```
or
```json
{"names": ["Example Fintech Pvt Ltd"]}
```
0.2cr per matched identifier; an unmatched one is free, so a claimed employer that
doesn't resolve costs nothing and is itself useful evidence (the claim may be
unconfirmable, or the company may be real but obscure — try `company/search` next
before concluding "can't verify").

## 4. Sanity-check seniority claims — `POST /company/enrich`
```json
{
  "crustdata_company_ids": [6036032],
  "fields": ["basic_info", "headcount", "funding"]
}
```
2cr/record; 15 RPM. `headcount` is a time series — pull the value closest to the
claimed date, not the current value, when checking "I led a 50-person team in 2023."

## 5. Market calibration — `POST /job/search`
```json
{
  "filters": {
    "op": "and",
    "conditions": [
      {"field": "title", "type": "=", "value": "Backend Engineer"},
      {"field": "location", "type": "=", "value": "Bengaluru"}
    ]
  },
  "limit": 20
}
```
30 RPM. Use this to check the brief's title against what the market actually calls the
role, and to show the recruiter comparable live postings — not to source candidates
directly.

## 6. Verify a claim Crustdata can't confirm — `POST /web/search/live`
```json
{"query": "\"Jane Doe\" conference talk payments infrastructure", "sources": ["news", "web"]}
```
1cr; **10 RPM — the bottleneck.** Budget this call for claims that are both
unconfirmed by `person/enrich` AND load-bearing for the ranking (don't burn this
endpoint on nice-to-have claims).

## 7. Pull the exact passage — `POST /web/fetch`
```json
{"url": "https://example.com/conference/2025/speakers"}
```
The citation must quote this page's own text, never the search snippet from step 6 — a
page about the same topic is not a source per the rulebook.

## 8. Re-engagement watcher — `POST /watch/...`
Handbook, Annexure C: "a webhook when a person, company or job posting you watch
changes." Config shape (mirrors the company-search watcher):
```json
{
  "filters": {"...": "candidate or company filter"},
  "config": {"trigger": {"type": "interval", "every_hours": 24}, "max_results_per_run": 25},
  "notifications": [{"type": "webhook", "url": "$SANDBOX_WEBHOOK_URL"}]
}
```
Demo via the **free** test endpoint:
```
POST /watch/{id}/test
```
Confirm the exact watcher resource path and payload shape for a *person* watch (vs. the
documented company-search watch) against `docs.crustdata.com` at 9:00 AM — flagged
unverified in the premortem.

## When something fails
| What you see | What to do |
|---|---|
| 401 | Key not reaching us — resend as `authorization: Bearer YOUR_API_KEY`. |
| 402 | Credits exhausted — `GET /account/credits` (free) to check, then find the Crustdata team. |
| 403 | This key can't call that endpoint — check Endpoints in the dashboard. |
| 429 | Over the per-endpoint limit — backoff 1/2/4s, respect `x-ratelimit-reset`. |
| No results | Loosen one filter at a time; check exact values via Autocomplete. |

## Where Sourced touches the whole surface
Unlike a single-endpoint-chain idea, every pipeline step in `SPEC.md` needs a different
endpoint: `person/search` (find) → `person/enrich` (verify) → `company/identify` +
`company/enrich` (sanity-check employers and seniority) → `job/search` (calibrate) →
`web/search` + `web/fetch` (fill the gaps Crustdata can't settle) → `watch` (re-engage).
That's 8 of 8 documented endpoints, each doing a job nothing else in the pipeline can
do — not padding for coverage's own sake.
