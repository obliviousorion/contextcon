VERDICT: PASS

1. backend/platform/actions.py:141-165 — webhook now requires https and a host in sandbox.allowed_hosts (config.yaml:33 is empty, so outbox only); otherwise it falls back to state/sandbox_outbox.jsonl. Verified OK. Minor: urllib follows redirects, so an allowed host could redirect elsewhere — fix: use a no-redirect opener (optional).
2. backend/crust/client.py:260-264 — person/search and person/enrich return EndpointDisabled. No call branches remain in backend/. Verified OK.
3. backend/platform/mcp_server.py:131 — still no approve tool. `issue` returns held_for_approval for anything unapproved. Verified OK.
4. README.md, docs/ — no personal data. The Rs 600 price is labelled "ESTIMATE, not a quote". The margin is labelled as arithmetic on an estimate. The measured cost (7.8 credits, 2026-11-22) cites its ledger. Thin records give an evidence request, "Not a negative finding", never a rejection. STALE never acts automatically. Approval is CLI only. OK.
5. fixtures/live_check/ — a grep for Bearer, sk-, authorization and api key found no secrets. The long hex matches are cache filenames and public company logo URLs. "token_limit_rpm" and "license_key" are field names in permissions_disabled.json, not values. Only company data. state/ has nothing. The only "Bearer" in the repo is backend/crust/client.py:178, which builds the header from the loaded key at runtime. OK.

FAILING TESTS: none observed (static review only; tests were not run).
