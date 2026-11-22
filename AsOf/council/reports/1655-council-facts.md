VERDICT: PASS
FINDINGS:
1. NOTES.md:5 — stale: still says C17 is UNVERIFIED and resolves to Delhivery 5798; Phase 4 settled it as CANNOT_RESOLVE (5798 and 15944579) — rewrite to "settled 2026-11-22" (NOTES.md:6 web/fetch cost also stale: /web/enrich/live measured at 1.0/page; line 8 CREDIT_TO_INR note is also outdated).
2. tests/cases/hidden_test_cases.json:2 — `_about` still says "'UNVERIFIED' cases need a live record-mode call"; no case is UNVERIFIED now — drop the sentence.
3. frontend/fixtures/demo_casefile.json (attestation.entity.domains, evidence E1 excerpt) — lists drl.aero under Delhivery's domains and E1 excerpt "domains [delhivery.com, drl.aero] -> 5798"; this repeats the alias that Phase 4 says is not proof (drl.aero matches two companies). Not an attested value, but a reader may take it as an ownership claim — label the extra domain as "listed alias, unverified" or restrict Entity.domains to the identified domain.
4. frontend/fixtures/demo_casefile.json (existence line) — point_date "2026-11-22" for year_founded 2011 is the retrieval date, not a data-point date (pre-existing, passed round 1535; the statement says "Data point dated 2026-11-22") — informational only.

Checks run (MODE=replay, no live calls, no .env read):
- pytest: 166 passed, 0 failed.
- Recomputed from fixtures/live_check/enrich.json: C01 26656@2024-07-15, C02 first point 2022-11-28 (NOT_YET_RECORDED), C03 IPO 2022-05-24, C04 2011, C05 418@2019-12-30, C06 1715@2026-08-31 (not 1773), C07 nearest 2026-09-07 gap 38 (STALE_DATA). CLI replay output matched all seven; C17 CLI gives cannot_resolve with 5798 and 15944579 and a "missing" text.
- "was true on": only in docs/tests that forbid it; no output contains it. Statements use the config template.
- Labels present: "profile-derived count", "estimate". Subsequent events carry "not attested" and are never in line. No growth or ratio verdict in code, observe or fixtures (growth_percent only appears in raw recorded data).
- Evidence has field_path, point_date, retrieved_at. One id per company (entity_by_id); alias is not cached without its own identify.
- Ledger sum 7.8 credits and Rs 62.12 (2.2 x 0.30 x 94.12) check out against README and docs.
FAILING TESTS:
none
