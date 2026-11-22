VERDICT: PASS
(tests/e2e: 4 passed. models.py unchanged since 98856cc. config.yaml changed only by lead commit 5b7c5d3, one line. All other commits are lead-authored and touch only module folders, tests, agy/, and config.)
1. backend/crust/ledger.py:22 — DEFAULT_CREDIT_CAP = 400.0 is a hard-coded fallback; client.py:35 uses it as the default credit_cap. It is a safety backstop and callers pass the config cap, so it is not blocking. — Make credit_cap a required argument, or load it from config.
2. backend/platform/actions.py:12,158 — urllib.request is used outside backend/crust/. It is the sandbox webhook POST, guarded by the sandbox.allowed_hosts check at line 147. It is not a Crustdata call, so it is acceptable. — Keep the allow-list check on the only path to urlopen, and leave a comment saying it is not a Crustdata path.
3. backend/engine/rules.py:74 — literal 400 is a string truncation length (400 chars), not a threshold. — None.
4. backend/platform/runstate.py:48-96 — .get("elapsed", 0.0) and .get("holds", 0) default persisted-state fields to 0, not thresholds. — None.
5. backend/crust/filters.py — emits => and =<, never >= or <=. The other >= / <= hits in backend/crust are Python comparisons. — None.
6. NOTES.md — no unmerged change requests (the only open item is the unused job/search note). — None.
FAILING TESTS: none
