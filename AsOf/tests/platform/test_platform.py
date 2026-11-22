import asyncio
import json
import subprocess
import sys
from datetime import date
from pathlib import Path

import pytest
import yaml

from backend.crust.client import CrustClient
from backend.crust.ledger import CREDIT_TO_INR, Ledger, cost_summary
from backend.platform import actions, config, runstate, watchers
from backend.platform.util import SourceUnavailable, read_jsonl, with_retry

ROOT = Path(__file__).resolve().parents[2]


def test_credit_to_inr_from_config():
    assert config.credit_to_inr() == pytest.approx(0.30 * 94.12)  # usd_per_credit x inr_per_usd
    assert CREDIT_TO_INR == pytest.approx(config.credit_to_inr())


def test_cost_summary(tmp_path):
    led = Ledger("r1", tmp_path)
    led.add("/company/enrich", 2.0, False)
    led.add("/company/enrich", 0.0, True)
    cs = cost_summary("r1", tmp_path)
    assert (cs.credits, cs.calls, cs.cache_hits) == (2.0, 1, 1)
    assert cs.inr == pytest.approx(round(2.0 * CREDIT_TO_INR, 2))


def test_replay_zero_network_calls(tmp_path):
    c = CrustClient("rp", mode="replay", cache_dir=tmp_path / "c", ledger_dir=tmp_path / "l")
    r = asyncio.run(c.company_enrich({"domains": ["x.com"]}))
    assert not r.ok and r.kind == "replay_miss"
    assert c.network_calls == 0 and c.get_run_cost() == 0


def test_execute_once_and_reconcile(state):
    n = []
    actions.approve("k1")
    actions.execute("k1", "send_evidence_request", "t", lambda: n.append(1))
    actions.execute("k1", "send_evidence_request", "t", lambda: n.append(1))
    assert n == [1]
    assert [e["key"] for e in read_jsonl(actions.effects_path())] == ["k1"]


def test_pending_written_before_effect_and_reconciled(state):
    seen = {}

    def boom():
        seen["status"] = actions.get_record("k2").status
        raise RuntimeError("crash")
    actions.approve("k2")
    with pytest.raises(RuntimeError):
        actions.execute("k2", "issue_case_file", "t", boom)
    assert seen["status"] == "pending"
    # simulate: effect landed in the log but the process died before marking done
    actions.approve("k3")
    actions._save("k3", "issue_case_file", "t", "pending")
    from backend.platform.util import append_jsonl
    append_jsonl(actions.effects_path(), {"key": "k3"})
    n = []
    actions.execute("k3", "issue_case_file", "t", lambda: n.append(1))
    assert n == [] and actions.get_record("k3").status == "done"
    assert [e["key"] for e in read_jsonl(actions.effects_path())].count("k3") == 1


def test_double_approval_one_send(state):
    assert actions.approve("k") is True
    assert actions.approve("k") is False
    for _ in range(2):
        actions.execute_approved("k", "send_evidence_request", "t", lambda: actions.sandbox_send({"key": "k"}))
    assert len(read_jsonl(actions.outbox_path())) == 1
    assert len(read_jsonl(actions.effects_path())) == 1


def test_unapproved_is_held(state):
    assert actions.execute_approved("nope", "issue_case_file", "t", lambda: 1 / 0) is None


def test_chaos_kill_restart(state):
    env_state = str(state)
    cmd = f"{sys.executable} {ROOT}/tests/platform/demo_actions.py"
    import os
    env = {**os.environ, "ASOF_STATE_DIR": env_state}
    r = subprocess.run([sys.executable, str(ROOT / "council/chaos_kill.py"), "--cmd", cmd, "--effects",
                        str(state / "effects.jsonl"), "--rounds", "5", "--expect-keys", "3", "--seed", "7",
                        "--max-delay", "0.8"], env=env, capture_output=True, text=True, cwd=ROOT, timeout=200)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "CHAOS: PASS" in r.stdout


def _steps(calls):
    return [(n, (lambda res, n=n: calls.append(n) or n.upper())) for n in ("a", "b", "c")]


def test_resume_zero_new_calls(state, tmp_path):
    calls = []
    cost = lambda: 3.0  # noqa: E731
    r1 = runstate.run("run1", _steps(calls), cost_fn=cost)
    assert r1.status == "done" and calls == ["a", "b", "c"]
    r2 = runstate.run("run1", _steps(calls), cost_fn=cost)
    assert calls == ["a", "b", "c"] and r2.results == r1.results
    assert all(e.status == "cache_hit" for e in r2.events)


def test_resume_no_double_counted_credits(state, tmp_path):
    led = Ledger("run2", tmp_path)
    steps = [("a", lambda r: led.add("/x", 2.0, False) and 1), ("b", lambda r: led.add("/y", 2.0, False) and 2)]
    runstate.run("run2", steps, cost_fn=lambda: led.total)
    runstate.run("run2", steps, cost_fn=lambda: led.total)
    assert Ledger("run2", tmp_path).total == 4.0


def test_cap_lowered_mid_run_budget_held(state, tmp_path, monkeypatch):
    cfg = tmp_path / "cfg.yaml"
    base = yaml.safe_load((ROOT / "config.yaml").read_text())
    cfg.write_text(yaml.safe_dump(base))
    monkeypatch.setenv("ASOF_CONFIG", str(cfg))
    spent = {"v": 0.0}

    def a(res):
        spent["v"] += 5
        base["limits"]["credit_cap_per_run"] = 5  # operator lowers the cap mid-run
        cfg.write_text(yaml.safe_dump(base))
        return 1
    calls = []
    steps = [("a", a), ("b", lambda r: calls.append("b") or 2)]
    r = runstate.run("run3", steps, cost_fn=lambda: spent["v"])
    assert r.status == "BUDGET_HELD" and r.refusal_code == "BUDGET_HELD" and calls == []
    assert any(e.status == "held_for_approval" for e in r.events)
    base["limits"]["credit_cap_per_run"] = 40  # resume
    cfg.write_text(yaml.safe_dump(base))
    r2 = runstate.run("run3", steps, cost_fn=lambda: spent["v"])
    assert r2.status == "done" and calls == ["b"] and spent["v"] == 5


def test_time_limit_held(state):
    t = {"v": 0.0}
    def clock():
        t["v"] += 200
        return t["v"]
    r = runstate.run("run4", [("a", lambda r: 1), ("b", lambda r: 2)], cost_fn=lambda: 0, clock=clock)
    assert r.status == "BUDGET_HELD" and "time limit" in r.held_reason


def test_torn_state_recovered(state):
    runstate.run("run5", _steps([]), cost_fn=lambda: 0)
    p = state / "runs" / "run5.json"
    p.write_text(p.read_text()[:20])  # torn
    calls = []
    r = runstate.run("run5", _steps(calls), cost_fn=lambda: 0)
    assert r.recovered_torn and r.status == "done" and calls == ["a", "b", "c"]
    assert any(e.status == "error" for e in r.events)
    p.write_text("[1,2]")  # valid JSON, wrong shape
    assert runstate.run("run5", _steps([]), cost_fn=lambda: 0).recovered_torn


def test_duplicate_alert_noop(state):
    s1, new1 = watchers.on_alert("w1", 42, "headcount", date(2025, 1, 5), "h")
    s2, new2 = watchers.on_alert("w1", 42, "headcount", date(2025, 1, 5), "h")
    assert new1 and not new2 and s1.dedupe_key == s2.dedupe_key
    assert s1.dedupe_key == watchers.dedupe_key("w1", 42, "headcount", date(2025, 1, 5))
    assert len(read_jsonl(state / "watch_alerts.jsonl")) == 1


def test_watch_create_held_then_once(state):
    e = watchers.create("acme.com")
    assert e["status"] == "held_for_approval" and e["key"] == watchers.idempotency_key("acme.com")
    n = []
    assert watchers.activate(e["key"], lambda: n.append(1) or "wid")["status"] == "held_for_approval"
    actions.approve(e["key"])
    for _ in range(2):
        out = watchers.activate(e["key"], lambda: n.append(1) or "wid")
    assert n == [1] and out["status"] == "created" and out["watch_id"] == "wid"
    e2 = watchers.create("beta.com")
    actions.approve(e2["key"])
    import os
    os.environ["MODE"] = "replay"
    try:
        assert watchers.activate(e2["key"])["watch_id"] == "w-" + e2["key"][:12]
    finally:
        del os.environ["MODE"]
    snap, new = watchers.test("wid")
    snap2, new2 = watchers.test("wid")
    assert new and not new2 and snap.dedupe_key == snap2.dedupe_key and snap.signal_date == date.today()


def test_poll_dedupes(state):
    f = lambda wid: [{"field": "headcount", "signal_date": "2025-02-01", "snapshot_hash": "x"}] * 2  # noqa: E731
    out = watchers.poll(f, "w2", 7)
    assert [new for _, new in out] == [True, False]


def test_retry_then_source_unavailable():
    n = []
    def f():
        n.append(1)
        raise TimeoutError
    with pytest.raises(SourceUnavailable):
        with_retry(f, attempts=3, sleep=lambda s: None)
    assert len(n) == 3


def test_sandbox_outbox_when_no_webhook(state):
    assert actions.sandbox_send({"a": 1}) == "outbox"
    assert read_jsonl(actions.outbox_path()) == [{"a": 1}]


def test_mcp_lists_tools_and_costs():
    from backend.models import CostSummary
    from backend.platform.mcp_server import TOOL_NAMES, build_server

    class R:
        def model_dump_json(self):
            return json.dumps({"x": 1, "cost": CostSummary(credits=2, inr=52.8, calls=1).model_dump()})
    async def fake(**kw):
        return R()
    reg = {n: fake for n in TOOL_NAMES}
    srv = build_server(reg)
    tools = asyncio.run(srv.list_tools())
    assert sorted(t.name for t in tools) == sorted(TOOL_NAMES)
    out = asyncio.run(srv.call_tool("resolve", {"domain": "x.com"}))
    blob = json.dumps(out, default=lambda o: getattr(o, "text", str(o)))
    assert "52.8" in blob


def test_mcp_missing_pipeline_is_clear_error():
    from backend.platform.mcp_server import build_server
    async def bad(**kw):
        raise RuntimeError("no pipeline")
    srv = build_server({"resolve": bad})
    out = asyncio.run(srv.call_tool("resolve", {"domain": "x.com"}))
    assert "no pipeline" in json.dumps(out, default=lambda o: getattr(o, "text", str(o)))


def test_execute_gated_without_approval(state):
    n = []
    assert actions.execute("g", "issue_case_file", "t", lambda: n.append(1)) is None
    assert n == [] and not actions.effects_path().exists()


def test_mcp_has_no_approve_tool():
    from backend.platform.mcp_server import TOOL_NAMES
    assert "approve" not in TOOL_NAMES and {"issue", "cost"} <= set(TOOL_NAMES)


def test_non_https_webhook_falls_back(state, monkeypatch):
    monkeypatch.setenv("SANDBOX_WEBHOOK_URL", "http://evil.example/x")
    assert actions.sandbox_send({"a": 1}) == "outbox"


def test_person_endpoints_disabled_no_network(tmp_path):
    c = CrustClient("pp", mode="live", api_key="x", cache_dir=tmp_path / "c", ledger_dir=tmp_path / "l")
    for f in (c.person_search, c.person_enrich):
        r = asyncio.run(f({}))
        assert not r.ok and r.kind == "endpoint_disabled" and "personal data" in r.reason
    assert c.network_calls == 0


def test_exceed_budget_approval_continues_once(state, tmp_path, monkeypatch):
    cfg = tmp_path / "cfg.yaml"
    base = yaml.safe_load((ROOT / "config.yaml").read_text())
    base["limits"]["credit_cap_per_run"] = 5
    cfg.write_text(yaml.safe_dump(base))
    monkeypatch.setenv("ASOF_CONFIG", str(cfg))
    calls = []
    steps = [("a", lambda r: calls.append("a") or 1), ("b", lambda r: calls.append("b") or 2)]
    r = runstate.run("eb", steps, cost_fn=lambda: 9.0)
    assert r.status == "BUDGET_HELD"
    key = [e for e in r.events if e.status == "held_for_approval"][0].data["approval_key"]
    assert actions.get_record(key).action == "exceed_budget" and actions.get_record(key).status == "pending"
    actions.approve(key)
    r2 = runstate.run("eb", steps, cost_fn=lambda: 9.0)
    assert r2.status == "done" and calls == ["a", "b"]


def test_append_jsonl_heals_torn_tail(state):
    from backend.platform.util import append_jsonl
    p = state / "x.jsonl"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text('{"key": "a"}\n{"key": "b"')  # torn tail, no newline
    append_jsonl(p, {"key": "c"})
    assert [e["key"] for e in read_jsonl(p)] == ["a", "c"]


def test_ledger_skips_torn_lines(tmp_path):
    led = Ledger("t", tmp_path)
    led.add("/a", 1.0, False)
    led.add("/a", 1.0, False)
    p = tmp_path / "t.jsonl"
    lines = p.read_text().splitlines()
    p.write_text(lines[0] + "\n{torn garbage\n" + lines[1] + "\n{\"run_id\": \"t\", \"ts")
    assert Ledger("t", tmp_path).total == 2.0
    l2 = Ledger("t", tmp_path)
    l2.add("/a", 1.0, False)  # heals tail, appends
    assert Ledger("t", tmp_path).total == 3.0


def test_identify_priced():
    from backend.crust.ledger import PRICES
    assert PRICES["/company/identify"] == 0.2


def test_runstate_wrong_typed_fields_quarantined(state):
    runstate.run("rw", _steps([]), cost_fn=lambda: 0)
    p = state / "runs" / "rw.json"
    p.write_text(json.dumps({"steps": {}, "elapsed": "garbage"}))
    r = runstate.run("rw", _steps([]), cost_fn=lambda: 0)
    assert r.recovered_torn and r.status == "done"


def test_sandbox_send_dedupes_on_key(state):
    actions.sandbox_send({"idempotency_key": "z", "n": 1})
    actions.sandbox_send({"idempotency_key": "z", "n": 2})
    assert len(read_jsonl(actions.outbox_path())) == 1


def test_webhook_allow_list_empty_means_outbox(tmp_path, monkeypatch):
    from backend.platform import actions
    monkeypatch.setenv("ASOF_STATE_DIR", str(tmp_path))
    monkeypatch.setenv("SANDBOX_WEBHOOK_URL", "https://hooks.example.com/x")
    posted = []
    monkeypatch.setattr(actions.urllib.request, "urlopen", lambda *a, **k: posted.append(a) or (_ for _ in ()).throw(AssertionError("network")))
    monkeypatch.setattr(actions, "load_config", lambda: {"sandbox": {"allowed_hosts": []}})
    assert actions.sandbox_send({"key": "k1"}) == "outbox" and not posted
    monkeypatch.setattr(actions, "load_config", lambda: {"sandbox": {"allowed_hosts": ["other.example.com"]}})
    assert actions.sandbox_send({"key": "k2"}) == "outbox" and not posted


def test_webhook_allowed_host_posts(tmp_path, monkeypatch):
    from backend.platform import actions
    monkeypatch.setenv("ASOF_STATE_DIR", str(tmp_path))
    monkeypatch.setenv("SANDBOX_WEBHOOK_URL", "https://hooks.example.com/x")
    monkeypatch.setattr(actions, "load_config", lambda: {"sandbox": {"allowed_hosts": ["hooks.example.com"]}})
    calls = []

    class R:
        def __enter__(self): return self
        def __exit__(self, *a): return False
        def read(self): return b""
    monkeypatch.setattr(actions.urllib.request, "urlopen", lambda *a, **k: calls.append(a) or R())
    assert actions.sandbox_send({"key": "k"}) == "webhook" and len(calls) == 1


def test_torn_ledger_tail_never_undercounts(tmp_path):
    led = Ledger("tt", tmp_path)
    led.add("/a", 1.0, False)
    iid = led.intent("/company/enrich", 2.0)
    p = tmp_path / "tt.jsonl"
    # kill during the done write: torn final line, intent unresolved
    with p.open("a") as f:
        f.write('{"run_id": "tt", "ts": "x", "endpoint": "/company/enr')
    assert Ledger("tt", tmp_path).total == 3.0  # 1 confirmed + 2 reserved
    l2 = Ledger("tt", tmp_path)
    l2.add("/b", 2.0, False, iid)  # a resolved intent is not double counted
    assert Ledger("tt", tmp_path).total == 3.0
    iid2 = l2.intent("/x", 1.0)
    l2.release(iid2)
    assert Ledger("tt", tmp_path).total == 3.0


def test_missing_config_key_fails_loudly():
    import pytest
    from backend.platform.config import limits
    with pytest.raises(KeyError, match="limits.credit_cap_per_run"):
        limits({"limits": {}})
