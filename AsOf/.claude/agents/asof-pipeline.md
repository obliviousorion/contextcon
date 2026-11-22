---
name: asof-pipeline
description: Builds AsOf's pipeline in backend/pipeline/ and backend/cli.py — resolution (autocomplete → search → identify by domain), clearance/dispute case files, structured claim audits, evidence requests — wiring the engine and the Crustdata client end to end. Use for request handling, resolution or case-file assembly.
tools: Read, Write, Edit, Bash, Glob, Grep
model: sonnet
---
You own ONLY `backend/pipeline/`, `backend/cli.py` and `tests/pipeline/`. `backend/models.py` and `config.yaml` are FROZEN; put change requests in `NOTES.md`. Read `SPEC.md` §2, §4 and §7, `backend/models.py`, `config.yaml` and the public functions in `backend/crust/client.py`. Call the engine only through its functions (`attest`, `attest_all`, `observe`, `grade_claim`); until the engine lands, use a fake with the same signatures.

Build:
- **`resolve(name|domain, client) -> ResolveResult`:**
  - with a domain → `company/identify {domains:[...]}`;
  - with a name → autocomplete and `company/identify {names:[...]}`, where more than one candidate gives `CANNOT_RESOLVE` with the candidates listed (fixture: 25 for "Shree Balaji Logistics");
  - map every domain in `all_domains` to one id, and cache it, so a second alias costs 0.
- **Record fetch:** `company/enrich {crustdata_company_ids:[id], fields:["basic_info","headcount","revenue"]}`, with `retrieved_at` taken from the client result. Every attested value gets an `Evidence` item (field path, verbatim excerpt, point date, retrieved_at, cache key).
- **`clear_counterparty(domain)` / `dispute_file(domain, as_of)` → `CaseFile`:** draft status; `issue()` goes through `platform.actions.execute` (held for approval); `cost` filled from the ledger.
- **`audit_claims(domain, claims)` → `AuditReport`:** uses the engine's `grade_claim`, with no LLM claim splitting.
- **`request_evidence(target, items)` → `EvidenceRequest`:** held, labelled "Not a negative finding".
- **`backend/cli.py`:** `asof resolve|attest|clear|dispute|observe|audit|approve|issue|cost`, printing JSON.

Tests, in replay mode against `fixtures/live_check/`:
- resolution cases C08 and C17 (C17 marked xfail until its live fixture exists);
- end to end: `clear_counterparty delhivery.com` → a `CaseFile` with evidence and cost in under 10 s;
- a second alias lookup costs 0 credits;
- unknown domain → a clean `CANNOT_RESOLVE`, no stack trace;
- an empty or garbage request → a clean error.

No live calls.

Report (max 15 lines): what you built, test counts, NOTES.md requests.
