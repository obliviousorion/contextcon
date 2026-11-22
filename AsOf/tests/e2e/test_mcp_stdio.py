"""E2E: the MCP server answers through the real stdio protocol (SPEC §7). Replay mode, 0 credits."""
import json
import os
import sys
from pathlib import Path

from mcp import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client

ROOT = Path(__file__).resolve().parents[2]
EXPECTED_TOOLS = {"resolve", "attest", "clear_counterparty", "dispute_file", "observe",
                  "audit_claims", "request_evidence", "watch", "issue", "cost"}


def _payload(result) -> dict:
    sc = getattr(result, "structured_content", None) or getattr(result, "structuredContent", None)
    if sc:
        return sc.get("result", sc) if set(sc) == {"result"} else sc
    return json.loads(result.content[0].text)


async def test_mcp_stdio_lists_tools_and_answers_c01(tmp_path):
    env = {**os.environ, "MODE": "replay", "ASOF_STATE_DIR": str(tmp_path)}
    params = StdioServerParameters(command=sys.executable, args=["-m", "backend.platform.mcp_server"],
                                   cwd=str(ROOT), env=env)
    async with stdio_client(params) as (r, w):
        async with ClientSession(r, w) as s:
            await s.initialize()
            names = {t.name for t in (await s.list_tools()).tools}
            assert EXPECTED_TOOLS <= names, names
            res = await s.call_tool("attest", {"domain": "delhivery.com", "field": "headcount", "as_of": "2024-07-15"})
            assert not res.isError if hasattr(res, "isError") else True
            out = _payload(res)
            line = out["result"]
            assert line["status"] == "attested"
            assert line["value"] == 26656
            assert line["point_date"] == "2024-07-15"
            assert line["label"] == "profile-derived count"
            assert "was true on" not in json.dumps(out)
            assert "cost" in out


async def test_mcp_has_no_approve_tool(tmp_path):
    """Approval is human-only (CLI). An agent connected over MCP must not be able to approve its own sends."""
    env = {**os.environ, "MODE": "replay", "ASOF_STATE_DIR": str(tmp_path)}
    params = StdioServerParameters(command=sys.executable, args=["-m", "backend.platform.mcp_server"],
                                   cwd=str(ROOT), env=env)
    async with stdio_client(params) as (r, w):
        async with ClientSession(r, w) as s:
            await s.initialize()
            names = {t.name for t in (await s.list_tools()).tools}
            assert "approve" not in names


async def test_mcp_issue_and_cost_use_the_real_pipeline(tmp_path):
    """Default registry, real protocol: issue on an unapproved case file is held; cost returns the ledger view."""
    env = {**os.environ, "MODE": "replay", "ASOF_STATE_DIR": str(tmp_path)}
    params = StdioServerParameters(command=sys.executable, args=["-m", "backend.platform.mcp_server"],
                                   cwd=str(ROOT), env=env)
    async with stdio_client(params) as (r, w):
        async with ClientSession(r, w) as s:
            await s.initialize()
            cf = _payload(await s.call_tool("clear_counterparty", {"domain": "delhivery.com"}))
            assert "error" not in cf, cf
            cf_id = cf["result"]["id"]
            held = _payload(await s.call_tool("issue", {"id": cf_id}))
            assert "error" not in held, held
            assert held["result"]["status"] == "held_for_approval"
            assert not (tmp_path / "sandbox_outbox.jsonl").exists()
            cost = _payload(await s.call_tool("cost", {}))
            assert "error" not in cost, cost
            assert "58.08" in json.dumps(cost)
