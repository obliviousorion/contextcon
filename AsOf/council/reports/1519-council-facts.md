VERDICT: FAIL

FINDINGS:
1. backend/engine/rules.py (existence attest) — attested existence line has point_date null and its Evidence (basic_info.year_founded) has point_date null, so check 8 (every attested value carries field path + point date + retrieved_at) fails; statement reads "Data point dated n/a" which departs from the config template — fix: either refuse existence (CANNOT_ATTEST, undated) or attach a documented point date (e.g. retrieval date with label "as recorded, undated") so the Evidence has a date; repro: `ASOF_STATE_DIR=$(mktemp -d) uv run python -m backend.cli attest delhivery.com existence 2024-07-15` (line.point_date null, evidence.E1.point_date null). Note C04 only requires value 2011, so a dated variant still passes.
2. backend/engine/rules.py (domains statement) — domains statement appends "True at retrieval only; this is not a historical record..." and refusal/subsequent-event statements append text beyond the config template. Not wrong in substance; no "was true on" anywhere (grep clean: only the forbidden-phrase guard and 2 tests). Optional: keep the label in `label` and trim the suffix — repro: `attest delhivery.com domains 2024-07-15`. LOW, non-blocking.
3. backend/engine/rules.py:18 — `_RATIO_TOKENS` uses substring match including "rate", "change", "delta"; a future field such as "exchange" would be routed to a no-verdict ratio audit (safe direction, over-refuses). LOW, non-blocking.

ACCEPT/REJECT of lead's judgement calls:
- first+latest post-D subsequent events: accept (never attested; status "subsequent_event").
- null on latest point -> CANNOT_ATTEST with no fallback: accept (shreebalajigrp revenue_band shows missing path and date).
- listing after D -> NOT_YET_RECORDED, "as recorded" labels: accept.
- existence "dated n/a": REJECT (finding 1).
- domains point_date = retrieval date: accept; the statement does say retrieval-only and the label is "true at retrieval only".
- refusal wording outside the template: accept; every refusal names what is missing (checked NOT_YET_RECORDED, STALE_DATA 38d, FUTURE_DATE, NO_RECORD_TYPE, CANNOT_ATTEST for year_founded, ipo_date, null revenue).
- growth -> cannot_verify with both dated values: accept; no ratio/growth number computed anywhere (grep of backend/).
- replay cost credits 0 + recorded 2.2 / Rs 58.08: accept; consistent in every output (0.2 / 5.28 for single-fixture paths).

CHECKS RUN:
- Recomputed from fixtures/live_check/enrich.json: 12 headcount cases (C01, C02, C05, C06, C07, C09, C10 plus 5 extra dates for delhivery/tci/shreebalaji incl. 2023-03-10, 2025-12-31, 2026-11-16) — value, point_date, refusal and gap_days all match the engine.
- Labels: headcount "profile-derived count", revenue_band "estimate", domains "true at retrieval only": correct in attest and clear output.
- Subsequent events carry status subsequent_event, never attested.
- Two domains (delhivery.com and drl.aero) both resolve to crustdata_company_id 5798 (C17 value holds in replay via all_domains; live identify still pending, xfail per brief).
- resolve --name "Shree Balaji Logistics" -> cannot_resolve, candidates listed, domain missing. Audit: agree/contradict (25% tolerance)/cannot_verify behave as configured.

FAILING TESTS:
none (129 passed, 1 xfailed = C17, expected).
