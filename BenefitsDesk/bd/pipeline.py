"""The run: a fixed list of steps per request type. Each step is saved in SQLite, keyed by a hash of
its inputs; on restart finished steps are skipped (and cost nothing). `--chaos` kills the process
at random step boundaries and inside the action protocol."""
from __future__ import annotations

import json
import os
import random
import time
from typing import Any, Callable

from . import actions, facts as F, insurers, peers, rules_engine as R
from .beliefs import beliefs_for
from .config import load_config, load_rules
from .crust import Crust
from .report import build_case
from .store import Store, h, now


class Run:
    def __init__(self, store: Store, request: dict, run_id: str | None = None, chaos: bool = False,
                 mode: str | None = None):
        self.store, self.req = store, request
        self.run_id = run_id or f"{request.get('id', 'run')}-{h(request)[:6]}"
        self.chaos_on = chaos
        self.p_kill = float(os.environ.get("BD_CHAOS_P") or load_config()["chaos"]["kill_probability"])
        self.mode = mode
        self.t0 = time.time()
        self.skipped: list[str] = []
        self.cannot: list[dict] = []
        self.questions: list[dict] = []
        if not store.q("SELECT 1 FROM runs WHERE run_id=?", self.run_id):
            store.x("INSERT INTO runs VALUES (?,?,?,?,?,?)", self.run_id, json.dumps(request), "running", now(), None, None)
        else:
            store.x("UPDATE runs SET status='running' WHERE run_id=?", self.run_id)
            store.event(self.run_id, "run", "resumed", "restart: finished steps will be skipped")

    # ---- chaos ------------------------------------------------------------
    def chaos(self, where: str) -> None:
        if self.chaos_on and random.random() < self.p_kill:
            self.store.event(self.run_id, where, "killed", "chaos kill")
            os._exit(137)

    # ---- steps ------------------------------------------------------------
    def crust(self, step: str) -> Crust:
        return Crust(self.store, self.run_id, step, mode=self.mode, started=self.t0)

    def step(self, name: str, inputs: Any, fn: Callable[[], Any]) -> Any:
        key = h(name, inputs)
        out = self.store.step_get(key)
        if out is not None:
            self.skipped.append(name)
            self.store.event(self.run_id, name, "skipped", "reused from step store")
            return out
        self.store.event(self.run_id, name, "start")
        if os.environ.get("BD_STEP_DELAY"):  # UI pacing only (config ui.step_delay_seconds), so a kill can land
            time.sleep(float(os.environ["BD_STEP_DELAY"]))
        self.chaos(f"before:{name}")
        out = fn()
        self.store.step_put(key, self.run_id, name, out)
        self.store.event(self.run_id, name, "done")
        self.chaos(f"after:{name}")
        return out

    # ---- request types ----------------------------------------------------
    def go(self) -> dict:
        t = self.req["type"]
        as_of = self.req.get("as_of") or "2026-11-22"
        since = self.req.get("since") or load_rules()["dates"]["window_start"]
        case: dict = {"run_id": self.run_id, "request": self.req, "as_of": as_of, "status": "finished"}
        try:
            if t in ("employee_review", "job_change_check"):
                self._persona(case, as_of, since, full=(t == "employee_review"))
            elif t == "peer_benchmark":
                case["peer_benchmark"] = self.step("peer_benchmark", [since, as_of, load_rules()["peer_benchmark"]],
                                                   lambda: peers.benchmark(self.crust("peer_benchmark"), since, as_of))
            elif t == "employer_package":
                self._employer(case, as_of, since)
            else:
                raise F.Refused("BAD_REQUEST", f"unknown request type {t!r}")
            if case["status"] != "refused":
                self._act(case)
        except F.Refused as e:
            case.update(status="refused", refusal={"code": e.code, "message": e.msg})
            self.store.event(self.run_id, "refused", "held", e.msg)
        except peers.HeldRun as e:
            case.update(status="held")
            self.cannot.append({"statement": "The run stopped at its limit before finishing", "missing": str(e)})
            self.store.event(self.run_id, "limits", "held", str(e))
        case.setdefault("questions", []).extend(self.questions)
        case.setdefault("cannot_verify", []).extend(self.cannot)
        case["skipped_steps"] = self.skipped
        case = build_case(self.store, case, self.run_id, time.time() - self.t0)
        self.store.x("UPDATE runs SET status=?, finished=?, result=? WHERE run_id=?", case["status"], now(),
                     json.dumps(case, default=str), self.run_id)
        self.store.event(self.run_id, "run", "finished", case["status"])
        return case

    def _persona(self, case: dict, as_of: str, since: str, full: bool) -> None:
        p = self.req.get("persona") or {}
        persona = self.step("sign_up", [p.get("profile_url"), p.get("consent"), p.get("answers")],
                            lambda: F.sign_up(self.store, p))
        pid = persona["persona_id"]
        case["persona"] = persona
        answers = p.get("answers") or {}
        flist = F.told_facts(answers, now()) if full else []
        rec = self.step("person_record", [F.normalize_url(p["profile_url"])],
                        lambda: _record(self.crust("person_record"), p["profile_url"]))
        alarm = None
        if rec["status"] == "redacted":
            raise F.Refused("RECORD_REMOVED", "This person's record has been removed at their request, so we do "
                            "not process it. Nothing was stored from it.")
        if rec["status"] == "error":
            self.cannot.append({"statement": "Employer facts", "missing": f"person record not settled: {rec['reason']}"})
        elif rec["status"] == "not_found":
            self.cannot.append({"statement": "Employer, job title, job dates",
                                "missing": "no public record for this profile; facts come from the person only"})
            self.questions.append({"question": "Who is your current employer, and since when?",
                                   "why": "No public record settles this; your answer will be labelled Told."})
        else:
            pd = rec["person_data"]
            chk, guesses = F.checked_facts(pd, rec["retrieved_at"])
            flist += chk + guesses
            for g in guesses:
                self.questions.append({"question": g["question"], "why": "Chosen by a guessed fact; the answer, not the guess, decides."})
            alarm = self.step("alarm", [rec["key"], since, as_of, load_rules()["job_change"], load_rules()["dates"]],
                              lambda: R.job_change(pd, since, as_of, rec["retrieved_at"]))
            case["alarm"] = alarm
            if alarm.get("sister_company"):
                self.questions.append({"question": "Your old and new employers are in one group. Did your cover change?",
                                       "why": "Treated as two employers; only you can confirm the cover."})
        self.questions.extend(F.conflicts(flist))
        for f in flist:
            if f.get("cannot_verify"):
                self.cannot.append({"statement": f["statement"], "missing": f.get("missing", "")})
        self._save_facts(pid, flist)
        case["facts"] = flist
        if full:
            case["peer_benchmark"] = self.step("peer_benchmark", [since, as_of, load_rules()["peer_benchmark"]],
                                               lambda: peers.benchmark(self.crust("peer_benchmark"), since, as_of))
            case["gaps"] = self.step("gaps", [flist, alarm, load_rules()["gaps"]], lambda: R.gaps(flist, alarm))
            case["shortlist"] = self.step("shortlist", [load_rules()["insurers"], as_of],
                                          lambda: insurers.shortlist(self.crust("shortlist"), as_of))
            for i in case["shortlist"]:
                for fg in i["figures"]:
                    if fg.get("cannot_verify"):
                        self.cannot.append({"statement": f"{i['insurer']}: {fg['metric']}", "missing": fg["missing"]})
            top = next((i for i in case["shortlist"] if i.get("rank") == 1), None)
            chosen = top["insurer"] if top else answers.get("chosen_insurer")
            basis = "ranked first on regulator figures" if top else "chosen by the person (told)"
            blocking = [q for q in self.questions if "conflict" in q["why"]]
            gaps_real = [g for g in case["gaps"] if g["severity"] != "low"]
            if not top:
                self.cannot.append({"statement": "Insurer ranking",
                                    "missing": "no insurer has 2 verified regulator figures, so none is ranked or recommended"})
            if gaps_real and chosen and not blocking:
                g = gaps_real[0]
                payload = {"insurer": chosen, "insurer_basis": basis, "cover": g["called_for"], "rule_id": g["rule_id"],
                           "applicant": {k: answers.get(k) for k in ("age_band", "dependants", "city", "cover_held")},
                           "premium": "to be quoted by the insurer"}
                self.step("prepare_application", [pid, payload], lambda: actions.prepare(
                    self.store, self.run_id, "submit_application", pid,
                    f"Submit a pre-filled application to {chosen} ({basis}) for {g['called_for']} (rule {g['rule_id']})",
                    payload)["key"])
            elif gaps_real and not chosen:
                self.questions.append({"question": "Which insurer would you like to apply to?",
                                       "why": "No insurer could be ranked on verified figures; we do not pick one for you."})
            elif blocking:
                self.questions.append({"question": "Please settle the conflicting fact above before we prepare an application.",
                                       "why": "We never prepare an application on a fact we have not settled."})
        if alarm and alarm["status"] == "job_change":
            payload = {"old_employer": alarm["old_employer"], "cover_end_date": alarm["cover_end_date"],
                       "convert_by": alarm["conversion_deadline"], "request": "convert group health cover to a personal policy"}
            self.step("prepare_conversion", [pid, payload], lambda: actions.prepare(
                self.store, self.run_id, "conversion_request", pid,
                f"Ask the group insurer to convert cover from {alarm['old_employer']} to a personal policy by {alarm['conversion_deadline']}",
                payload)["key"])

    def _employer(self, case: dict, as_of: str, since: str) -> None:
        case["peer_benchmark"] = self.step("peer_benchmark_roles", [since, as_of, load_rules()["peer_benchmark"]],
                                           lambda: peers.benchmark(self.crust("peer_benchmark_roles"), since, as_of, True))
        case["package"] = self.step("package", [load_rules()["package"]], lambda: R.package())
        g = self.req.get("group")
        if g:
            case["workplace"] = self.step("workplace", [g, load_rules()["beliefs"]],
                                          lambda: beliefs_for(self.store, self.crust("workplace"), g))

    def _save_facts(self, pid: str, flist: list[dict]) -> None:
        for f in flist:
            self.store.x("INSERT OR REPLACE INTO facts VALUES (?,?,?,?,?,?,?,?)", pid, f["fact_id"], f["statement"],
                         json.dumps(f.get("value")), f["label"], json.dumps(f.get("source")),
                         (f.get("source") or {}).get("record_date"), (f.get("source") or {}).get("retrieved_at"))

    def _act(self, case: dict) -> None:
        """Send every APPROVED action of this run, exactly once. Unapproved ones wait."""
        pid = (case.get("persona") or {}).get("persona_id")
        for it in actions.list_all(self.store, self.run_id, pid):
            if it["status"] in ("approved", "sending"):
                self.store.event(self.run_id, f"act:{it['action']}", "start")
                try:
                    actions.execute(self.store, it["key"], self.chaos)
                    self.store.event(self.run_id, f"act:{it['action']}", "done", "sent to sandbox once")
                except actions.SandboxDown as e:
                    self.store.event(self.run_id, f"act:{it['action']}", "held", f"sandbox unreachable: {e}")
                    case["status"] = "held"


def _record(c: Crust, url: str) -> dict:
    r = c.person_enrich(url)
    if r.kind == "held":
        raise peers.HeldRun(r.reason)
    if not r.ok:
        return {"status": "error", "reason": r.reason, "key": r.req_hash}
    status, pd, _ = F.person_entry(r.data)
    return {"status": status, "person_data": pd, "retrieved_at": r.retrieved_at, "key": r.req_hash}
