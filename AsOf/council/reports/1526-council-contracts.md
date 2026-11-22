VERDICT: FAIL

Scope: git diff --stat b7b31c7..HEAD (17 files).

Checks that pass
- backend/models.py and config.yaml: unchanged since b7b31c7. Lead-only rule holds.
- Folders: changes are only in backend/crust, backend/platform, backend/pipeline, backend/cli.py, tests/platform and tests/pipeline, plus STATUS.md and TODO.md. No module wrote outside its folders. backend/engine is untouched.
- Crustdata calls: httpx appears only in backend/crust. backend/platform/actions.py:12,150 uses urllib.request, but only for the sandbox webhook. It is https-only and not a Crustdata call (unchanged from 1519).
- Thresholds: no new hard-coded values. The 40 at pipeline/session.py:100 and platform/config.py:29 is a fallback default for config.limits.credit_cap_per_run. The 40 at api.py:35 and :91 is a string-truncation length. The 14 and 400 values are in engine/rules.py and are config-read defaults or truncation lengths, all unchanged.
- MCP tool set: TOOL_NAMES includes issue and cost, and approve is gone. No approve tool is registered.
- Async: call() awaits awaitables, and api.issue and api.cost are both async def. The await is correct.

FINDINGS:
1. backend/platform/mcp_server.py:133 — The MCP `issue` tool calls `call("issue", id=id)`, but `backend/pipeline/api.py:415` defines `async def issue(artifact_id: str)`. Through the protocol this raises TypeError (unexpected keyword 'id'), which `call()` swallows into an {"error": ...} result. The tool can never issue anything. The mcp_server.py:31 comment also documents `issue(id)`. — Fix: either change the MCP call to `call("issue", artifact_id=id)`, or rename the api parameter to `id`. Add a registry-free test that drives the real api.
2. backend/platform/mcp_server.py:136-138 — The MCP `cost(run_id)` tool forwards `run_id=...` when it is not None, but `api.cost()` at api.py:559 takes no parameters. Any call with run_id fails with a TypeError. Calls without it work. — Fix: give api.cost an optional `run_id: str | None = None` and filter on it, or drop run_id from the MCP tool.
3. Test gap — The platform tests use fake registries, so the mismatches in 1 and 2 are invisible. — Fix: add one MCP-protocol test that uses the default registry (real api) and calls issue and cost.

FAILING TESTS: none run (read-only review). The contract mismatches above are not covered by any test.
