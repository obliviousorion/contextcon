# Crustdata API cheat sheet (for Raise)

Checked against docs.crustdata.com on 2026-11-21. Anything not confirmed is marked UNVERIFIED. Recheck against real responses at 9 AM.

Base: `https://api.crustdata.com`. Headers: `authorization: Bearer KEY`, `x-api-version: 2025-11-01`, `content-type: application/json`.

**Filter grammar:**
- Single condition: `{"field","type","value"}`.
- Group: `{"op":"and"|"or","conditions":[...]}`. Groups can be nested.
- Operators: `= != < =< > => in not_in is_null is_not_null (.) [.] (!) contains not_contains has_all geo_distance`.
  - **Never use `>=` or `<=`**. They return "unknown operator". Write `=>` and `=<` instead.
  - `[.]` matches a phrase. `(.)` is a fuzzy match on all words.

## 1. Company Enrich: `POST /company/enrich`
- **Cost:** 2 credits per company. **Rate limit:** 15 per minute. **Batch size:** up to 25.
- **Identifiers:** pass exactly ONE type: `domains`, `names`, `crustdata_company_ids` or `professional_network_profile_urls`.
- **Fields:** defaults to `["basic_info"]`, so always pass `fields`.

```json
{"domains":["retool.com"],"fields":["basic_info","funding","competitors","people"]}
```
Response (a top-level array):
```json
[{"matched_on":"retool.com","matches":[{"confidence_score":1.0,"company_data":{
  "crustdata_company_id":633593,
  "funding":{"total_investment_usd":141000000.0,"last_fundraise_date":"YYYY-MM-DD","last_round_type":"series_c",
    "investors":["Liquid 2 Ventures","SV Angel"],
    "investors_detailed":[{"name":"","uuid":"","type":"","permalink":"","crunchbase_profile_url":""}],
    "milestones":[{"date":"","funding_date":"","amount_usd":0,"round_type":"series_a","investors":"<string>","lead_investors":"<string>"}]},
  "competitors":{"all_domains":["x.com"],"paid_seo":[],"organic_seo":[]},
  "people":{"founders":[{"crustdata_person_id":14540,"basic_profile":{"name":"..","current_title":".."},
     "social_handles":{"professional_network_identifier":{"profile_url":".."}},
     "experience":{"employment_details":{"current":[],"past":[]}}}],"decision_makers":[],"cxos":[]}}}]}]
```

**Watch out for:**
- `milestones[].lead_investors` and `milestones[].investors` are a **single string**, not a list. The delimiter is UNVERIFIED, so split defensively on `,`, `;` and ` and `.
- `funding.investors` is a list of strings covering all-time investors.
- `investors_detailed` has a Crunchbase uuid, but no domain and no Crustdata company id.
- `round_type` uses lowercase with underscores, for example `seed` and `series_a`. There are 28 values in total. Whether `pre_seed` exists is UNVERIFIED, so use autocomplete to get the full list.
- `competitors` contains domains only. Resolve them with Identify or Enrich.
- Founders already include `experience`, which may mean you don't need a separate Person Enrich call.

## 2. Company Search: `POST /company/search`
- **Cost:** 0.03 credits per result.
- **Surcharge:** +0.2 for each of the funding, headcount and hiring groups, charged once if you filter on the group and again if you return it.

```json
{"filters":{"op":"and","conditions":[
   {"field":"funding.investors","type":"in","value":["Sequoia Capital"]},
   {"field":"funding.last_round_type","type":"in","value":["seed","series_a"]},
   {"field":"funding.last_fundraise_date","type":"=>","value":"2024-01-01"},
   {"field":"locations.country","type":"in","value":["USA","IND"]},
   {"field":"basic_info.year_founded","type":">","value":2020}]},
 "search":{"query":"developer observability tools","mode":"hybrid"},
 "fields":["crustdata_company_id","basic_info.name","basic_info.primary_domain","funding"],
 "limit":20}
```
Response: `{"companies":[...],"next_cursor":"...","total_count":null}`

**Ranked search (with a query):**
- At most 1,000 results, and `limit` must be 1–100.
- `sorts` is not allowed.
- The cursor expires after 20 minutes.
- `mode` can be `hybrid` (the default), `lexical` or `semantic`. The query must not be empty.

**Filter-only search:**
- `limit` can be 1–1000.
- Sort with `{"field","order"}`.

**Searching by investor:** `funding.investors` with `in` needs an exact name match, so get the canonical spelling from autocomplete first. This filter does not tell you which round an investor joined.

**Other fields:**
- `locations.country`, using ISO-3 codes.
- `locations.city`.
- `taxonomy.categories` (801 values).
- `taxonomy.professional_network_industry`.
- `basic_info.industries`.
- `headcount.total`.

## 3. Person Search (partners at a firm): `POST /person/search`
- **Cost:** 0.03 credits per result.

```json
{"filters":{"op":"and","conditions":[
   {"field":"experience.employment_details.current.company_website_domain","type":"=","value":"sequoiacap.com"},
   {"op":"or","conditions":[
     {"field":"experience.employment_details.current.title","type":"[.]","value":"Partner"},
     {"field":"experience.employment_details.current.title","type":"[.]","value":"Principal"}]}]},
 "fields":["basic_profile.name","basic_profile.current_title","social_handles.professional_network_identifier.profile_url"],
 "limit":25}
```

**Matching the current employer.** All of these live under `...current.`:
- `company_name`. Use `[.]` for partial matches, because `=` requires an exact string.
- `company_id`, the Crustdata company id.
- `company_professional_network_profile_url`.

**Response:** `{"profiles":[{"crustdata_person_id","basic_profile":{name,current_title},"social_handles":{...profile_url}}],"total_count":12}`

**Design issue:** investors have no domain in the data. To get one, resolve the investor name with Identify (`names`), or fall back to `current.company_name [.] "<firm>"`.

## 4. Person Enrich: `POST /person/enrich`
- **Cost:** 1 credit per profile. **Rate limit:** 15 per minute. **Batch size:** up to 25.
- **Identifier:** `professional_network_profile_urls` only.

```json
{"professional_network_profile_urls":["https://www.linkedin.com/in/dvdhsu/"],"fields":["basic_profile","experience","social_handles"]}
```
Path to past roles: `matches[0].person_data.experience.employment_details.past[]`. Each entry has `{name,title,start_date,end_date,crustdata_company_id,company_website_domain}`.

**Overlap check:** match on `crustdata_company_id` first, then fall back to `company_website_domain`. Then compare the date ranges. Dates can be null, so handle missing values.

## 5. Discovery Watcher: `POST /watch/company/search`
```json
{"filters":{...same grammar as search...},
 "fields":["crustdata_company_id","basic_info.name","funding"],
 "config":{"trigger":{"type":"interval","every_hours":24},"max_results_per_run":25,"payload_delivery_type":"inline"},
 "notifications":[{"type":"slack","webhook_url":"https://hooks.slack.com/services/..."},
                  {"type":"webhook","url":"https://x/hook","headers":{"X-Token":"abc"}}],
 "preview":false}
```

**Notification channels:**
- **Native Slack** is supported with `{type:"slack",webhook_url}`.
- Other channel types are `google_chat` and `email {to:[]}`.

**Behaviour:**
- Filters can't be changed after the watch is created.
- `preview:true` is free and returns `{can_create,count,sample,credits}`.

**Cost:**
- The first run is free and returns up to 5 companies.
- After that it costs 2 credits per new company.

**Payload:** `{metadata:{watch_id,run_id,summary:{delivered,...}}, results:{added:[...]}}`

**Test endpoint:** `POST /watch/company/search/{id}/test` costs 0 credits. Send `{"notification_endpoint":"https://public.url/hook","count":3,"deliver":true}`.
- It returns 400 if the filter currently matches nothing, so **make sure the demo watch filter matches something.**
- It rejects localhost URLs, so use cloudflared or the native Slack type.

## 6. Company Identify: `POST /company/identify`
- **Cost:** 0.2 credits per match. **Rate limit:** 30 per minute. **Batch size:** up to 25.
- **Identifiers:** `domains`, `names`, `crustdata_company_ids` or `professional_network_profile_urls`.
- Returns `crustdata_company_id`, plus basic info with name, primary_domain, website, employee_count_range and industries.

## 7. Free and cheap endpoints (use them while developing)
- `POST /company/search/autocomplete` (free). Example: `{"field":"funding.investors","query":"sequoia","limit":20}` returns `{"suggestions":[{"value":".."}]}`.
  - Use it for canonical investor names.
  - Use it for round-type values: `field:"funding.last_round_type", query:""`.
  - An invalid field returns a 400 that lists the valid fields.
- `POST /person/search/autocomplete` (free). Example: `{"field":"experience.employment_details.current.title","query":"Partner"}`.
- `GET /account/credits` (free).
- `GET /account/endpoints` shows permissions and rate limits. Whether it's free is UNVERIFIED.
- Every response includes an `x-credits-used` header. Log it.

## Pipeline implications for Raise
1. Competitors come back as domains, so resolve them with Identify or Enrich (batch of 25).
2. Get lead investors by parsing the `milestones[].lead_investors` string. The ground truth for the eval also comes from here.
3. Build an investor alias map. Seed it from autocomplete plus normalization (lowercase, strip ventures/capital/partners/fund/llc).
4. For partners, resolve firm → domain (Identify by name), then run Person Search on the current domain + title. If that fails, fall back to a `company_name [.]` match.
5. For intro paths, use the founders' `experience` from Company Enrich and Person Enrich on the partners, then compare `past[]` by company id and date overlap.
