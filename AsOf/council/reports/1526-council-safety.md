VERDICT: PASS

Re-check of 1519 fixes. Full suite: 180 passed, 1 xfailed. Secret grep (backend, fixtures, agy, state): only the test literal "Bearer k"; other hex hits are ids and cache hashes. .env not opened.

Verified fixed:
- 1519#1: MCP has no approve tool. The issue tool says it sends only what a human approved via the CLI (mcp_server.py:131).
- 1519#2: execute holds any action in config approvals unless is_approved(key) (actions.py:86-93). exceed_budget is covered by the same list.
- 1519#3: non-https webhook falls back to the outbox (actions.py:146).
- 1519#4: person_search and person_enrich return EndpointDisabled with no network call (client.py:254-258).
- 1519#6: pipeline/api.py:390-412 refuses non-drafts and already-approved items, and stores approver and timestamp.
- 1519#5: the whole-repo scan, ../.env hash check (exit 3) and the double flag are present (run_task.sh:15-35). Report-not-revert is a defensible choice, because auto-reverting would destroy parallel agents' work. It is acceptable as long as the lead reviews every exit-3 result.
- 1519#7: README is pending (Phase 5), not a FAIL. Checks 6 (decision lines) and 7 (fee labels) must be re-run once it lands.

FINDINGS (non-blocking):
1. backend/platform/actions.py:146 — https is required, but there is no host allow-list, so a mis-set SANDBOX_WEBHOOK_URL could still send to an arbitrary https host — add a sandbox_hosts allow-list to config, or document the env var as trusted.
2. agy/run_task.sh:22-35 — the scan covers only git status in the repo. Writes outside the repo (such as ~) are invisible. Only ../.env is fingerprinted. Out-of-scope files are left in place — keep the lead's review step, and run the full-permissions flag only with the user's OK.
3. README.md — not yet written — re-check ₹ labels (estimate vs recorded) and evidence ids on decision lines after Phase 5.
4. backend/crust/ledger.py:27-29 — person endpoints still carry price entries. This is harmless now that they are disabled, but it is dead config — remove it when convenient.

FAILING TESTS: none.
