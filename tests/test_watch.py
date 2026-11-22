"""Checkpoint 9: the direct request and the watch path give the same result, and one action."""
import json
from pathlib import Path

from bd import actions, watch
from bd.crust import Crust, Result
from bd.pipeline import Run
from bd.store import Store

ROOT = Path(__file__).resolve().parents[1]
T1 = json.loads((ROOT / "requests" / "T1_job_change.json").read_text())


def t1_person_data():
    fx = json.loads((ROOT / "fixtures" / "crust" / "e7081182ca63d372.json").read_text())
    return fx["data"][0]["matches"][0]["person_data"]


def fake_api(runs, summaries):
    def call(self, path, body=None, method="POST", cacheable=True):
        self.store.ledger_add(self.run_id, self.step, path.split("?")[0], 0.0, 0.0, False, "ok", "test")
        if path.endswith("/summary"):
            rid = int(path.split("/")[-2])
            return Result(True, data=summaries[rid], retrieved_at="2026-11-22T11:00:00+00:00", endpoint=path)
        return Result(True, data={"runs": runs, "next_cursor": None, "total_count": len(runs)}, endpoint=path)
    return call


def test_watch_and_direct_path_agree_and_make_one_action(state, monkeypatch):
    s = Store()
    direct = Run(s, T1).go()  # direct request first
    watch.register(s, "w1", T1["persona"]["profile_url"])
    summary = {"id": 7, "status": "SUCCESS", "completed_at": "2026-11-22T11:00:00+00:00",
               "payload_delivery": {"type": "inline"},
               "notifications": [{"http_status": 200, "payload": {"notifications": [
                   {"uid": "person_x_7", "changes": [{"field": "experience.employment_details.current", "type": "added"}],
                    "record": t1_person_data()}]}}]}
    runs = [{"id": 6, "status": "SUCCESS", "new_records_count": 0},  # baseline run: nothing delivered
            {"id": 7, "status": "SUCCESS", "new_records_count": 1},
            {"id": 8, "status": "RUNNING", "new_records_count": 0}]
    monkeypatch.setattr(Crust, "call", fake_api(runs, {7: summary}))
    out = watch.pull(s, Crust(s, "watch-run", "watch"), "w1", "2026-09-01", "2026-11-22", "watch-run")
    a, d = out["alarms"][0], direct["alarm"]
    for k in ("status", "old_employer", "new_employer", "change_date", "cover_end_date", "conversion_deadline"):
        assert a[k] == d[k]
    assert out["processed_runs"] == [6, 7] and out["last_run_id"] == 7  # stops before the RUNNING run
    assert len([i for i in actions.list_all(s) if i["action"] == "conversion_request"]) == 1  # same key: one action
    again = watch.pull(s, Crust(s, "watch-run", "watch"), "w1", "2026-09-01", "2026-11-22", "watch-run")
    assert again["processed_runs"] == [] and again["alarms"] == []  # nothing handled twice


def test_only_opted_in_people_can_be_watched(state):
    import pytest
    with pytest.raises(ValueError):
        watch.register(Store(), "w2", "https://example.test/in/stranger")


def test_create_refuses_without_a_notification_channel(state):
    s = Store()
    assert watch.create(s, Crust(s, "x", "x"), "https://fixture.test/in/persona-t1-job-change")["created"] is False
