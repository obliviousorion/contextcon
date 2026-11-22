VERDICT: PASS

FINDINGS:
1. backend/engine/rules.py (existence) — 1519 finding 1 FIXED. attest delhivery.com existence 2024-07-15 now gives point_date = retrieval date 2026-11-22, label "as recorded", Evidence E1 with field_path basic_info.year_founded, point_date and retrieved_at; statement is the exact config template. LOW note: the "point date" for existence is the retrieval date, not a founding date, and is later than as_of; label "as recorded" is accepted but a reader may misread it. Non-blocking.
2. backend/engine/rules.py (statements) — 1519 finding 2 FIXED. Attested headcount/domains/existence statements are exactly "Data point dated P states X; stored copy retrieved T." with no suffix; domains carry the label "true at retrieval only". Refusal statements still extend beyond the template but each names what is missing (e.g. revenue_band: "missing a revenue.estimated.timeseries point dated on or before 2024-07-15; the first point is dated 2025-01-01"). Grep for "was true on": only the FORBIDDEN_PHRASE guard and models.py comment.
3. backend/engine/rules.py:18 — 1519 finding 3: _RATIO_TOKENS still lists "rate", "change", "delta" as fragments; the commit says matching is now whole-token (not re-derived here in depth). Safe direction either way. Non-blocking.

CHECKS RUN (replay, temp ASOF_STATE_DIR):
- attest existence/headcount/revenue_band/domains for delhivery.com 2024-07-15: dated, labelled correctly (headcount "profile-derived count", domains "true at retrieval only"); post-D points are status subsequent_event, never attested.
- clear delhivery.com: resolved id 5798 with domains drl.aero + delhivery.com; existence evidence dated.
- No undated attested line (0 null point_date on existence).

FAILING TESTS:
none (uv run pytest -q tests/engine: 99 passed; full tests: 163 passed, 1 xfailed = C17, known).
