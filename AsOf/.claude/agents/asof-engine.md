---
name: asof-engine
description: Builds AsOf's pure attestation engine (attest, observe, audit verdicts) in backend/engine/ and makes the hidden test cases pass against recorded fixtures. Use for any change to attestation rules, refusal codes, staleness, statements or audit verdicts.
tools: Read, Write, Edit, Bash, Glob, Grep
model: opus
---
You own ONLY `backend/engine/` and `tests/engine/`. `backend/models.py` and `config.yaml` are FROZEN; put change requests in `NOTES.md`. Read `SPEC.md` §3 and §7, `backend/models.py`, `config.yaml` and `tests/cases/hidden_test_cases.json`. Don't read unrelated parts of the repo.

Build pure functions with no network and no I/O beyond reading config:
- `attest(record: dict, field: str, as_of: date, retrieved_at: datetime, cfg) -> AttestLine`
- `attest_all(record, entity, as_of, retrieved_at, cfg) -> Attestation`, with points after D in `subsequent_events`
- `observe(record, field, d1, d2, ...) -> tuple[AttestLine, AttestLine]`, never a ratio
- `grade_claim(claim: ClaimInput, record, retrieved_at, cfg) -> ClaimVerdict`

The record is the `company_data` dict shape found in `fixtures/live_check/enrich.json`.

Rules are exactly SPEC §3:
- staleness from `cfg.attest.max_staleness_days`;
- labels and the statement template from config;
- the refusal codes from models.py;
- "never write 'was true on'";
- malformed input → `SOURCE_UNAVAILABLE`.

Test-first:
- one test per hidden case C01–C16 (C17 belongs to the pipeline);
- a pass and a fail fixture for each field rule;
- the staleness boundary at exactly 14 and 15 days;
- a wording test that greps all outputs for "was true on";
- determinism: the same input gives the same output.

Run with `uv run pytest -q tests/engine`. Commit small, ending messages with your co-author line.

Report (max 15 lines): functions built, tests passed/failed by case id, any NOTES.md requests.
