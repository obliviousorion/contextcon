TASK: AsOf web UI (cut first if time is short). Allowed: frontend/ only.
Read SPEC.md §2 and §10, backend/models.py and tests/cases/hidden_test_cases.json.
1. Create frontend/fixtures/demo_casefile.json: a realistic CaseFile JSON for delhivery.com, kind "clearance", built ONLY from values in fixtures/live_check/enrich.json (founded 2011, IPO 2022-05-24, the latest headcount point and its date, domains labelled "true at retrieval only", revenue band labelled "estimate"). Also create demo_refusals.json with the C02, C07 and C08 outcomes from the hidden cases.
2. Build a single-page app with Vite, React, TypeScript and Tailwind in frontend/:
   - a request bar: tool (clear / dispute / attest / resolve), domain, as-of date;
   - the case file: each line shows its status chip (attested / cannot attest / subsequent event), value, label, point date, retrieved-at, and a source chip that opens the evidence (field path and excerpt); refusals show refusal_code and "missing";
   - a cost panel with credits and ₹;
   - an "Approve & issue" button that disables after one click and shows "held for approval" → "issued (sandbox)";
   - a "Move the date" slider that switches between fixture outcomes.
   It reads the fixture files by default; an env var VITE_API_URL switches it to a real API later.
3. `npm run build` must succeed with no TypeScript errors. Add frontend/README.md with run steps.
