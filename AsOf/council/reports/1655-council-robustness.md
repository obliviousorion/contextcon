VERDICT: PASS

FINDINGS: none blocking. Minor, non-blocking:
1. backend/crust/client.py:93 — `_estimate` returns a flat 1.0 for /web/enrich/live, but `_credits` charges 1.0 per URL, so the pre-flight cap check under-estimates a multi-URL web_fetch. Nothing in backend/ calls web_fetch today, so it has no effect now. — Fix: estimate `1.0 * len(body["urls"])` the way /company/enrich does.
2. backend/pipeline/resolver.py:51-58 — After the Phase 4 change, the resolved Delhivery entity still lists drl.aero in `domains` (display only). The `entities` cache is keyed only by the identified domain, so drl.aero re-identifies and stays cannot_resolve. Confirmed in replay. — Cosmetic: filter the displayed aliases, or leave as is.
3. Carried over from 1535: a torn ledger tail can undercount by at most one call, and the CLI default is MODE=live when MODE is unset. Both are unchanged.

EVIDENCE (HEAD, MODE=replay, no network, no .env read):
- `pytest tests backend` gave 183 passed. Existing tests cover double approval, resume with 0 calls and no double-counted credits, torn state and torn ledger, cap lowered mid-run giving budget_held, 5xx retry then unavailable, malformed response, duplicate alert no-op, and garbage requests.
- Chaos, demo_actions.py (3 actions, `--rounds 5 --expect-keys 3 --max-delay 0.8`):
  - Seed 3: effects=3 distinct=3, CHAOS: PASS.
  - Seed 21: kills mid-run, effects=3 distinct=3, CHAOS: PASS.
- Chaos on the real path (/tmp/rb1655/real.py: request_evidence, approve, then issue twice; `--rounds 5 --expect-keys 1 --max-delay 0.4`):
  - Seed 5: all rounds finished, effects=1, PASS.
  - Seed 9: 4 of 5 rounds killed at 0.21s, 0.18s, 0.10s and 0.05s, effects=1 distinct=1 torn=0, PASS.
  - Seed 14: kills at 0.09s and 0.14s, effects=1, PASS.
- Mocked timeout (respx ReadTimeout on /company/identify): retried 4 times, then returned ok=False "retries exhausted (transport error)", never an answer. A 200 non-JSON body on /web/enrich/live returned ok=False.
- Edge requests through the pipeline API: empty, whitespace, control characters, "not a domain!!", a 400-character URL, None, an int, a bad as_of, an empty audit, a garbage audit and an empty evidence target all raised a clean RequestError with no stack trace.
- Replay with unknown domain nonexistent-zzz.example gave cannot_resolve (replay_miss), with no answer and ledger 0.0.
- drl.aero gave cannot_resolve with candidates 5798 and 15944579. delhivery.com resolved.
- All 12 merged cache fixtures parse as JSON. Ledger phase4-record-2026-11-22.jsonl is consistent: identify 0.2, web/enrich/live 1.0, and the cf-* runs at 0.2 plus 2.0 each.
- ReplayIndex removal: no dangling references, and a replay miss is now an error, not an inference.

FAILING TESTS: none.
