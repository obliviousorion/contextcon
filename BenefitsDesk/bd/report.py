"""Case file: keep only the sections config.yaml lists, add actions and cost, render Markdown."""
from __future__ import annotations

import json

from . import actions
from .config import load_config
from .store import Store


def build_case(store: Store, case: dict, run_id: str, seconds: float) -> dict:
    cfg = load_config()
    case["actions"] = actions.list_all(store, run_id, (case.get("persona") or {}).get("persona_id"))
    case["cost"] = {**store.run_cost(run_id), "seconds": round(seconds, 2),
                    "cap": cfg["limits"]["credit_cap_per_run"], "inr_per_credit": cfg["cost"]["inr_per_credit"]}
    keep = ["run_id", "status", "as_of", "skipped_steps", "refusal"] + list(cfg["output"]["fields"])
    return {k: case[k] for k in keep if k in case}


def markdown(case: dict) -> str:
    L = [f"# Case file {case['run_id']}", "",
         f"Status: **{case['status']}** · as of {case.get('as_of')} · cost {case['cost']['credits']} credits "
         f"(Rs {case['cost']['inr']}) · {case['cost']['calls']} calls, {case['cost']['cache_hits']} cache hits · "
         f"{case['cost']['seconds']} s", ""]
    if case.get("refusal"):
        L += [f"**Refused ({case['refusal']['code']}):** {case['refusal']['message']}", ""]
    if case.get("request"):
        L += [f"> {case['request'].get('said', '')}", ""]
    if case.get("facts"):
        L += ["## Fact file", "", "| Label | Fact | Source (field, date) |", "|---|---|---|"]
        for f in case["facts"]:
            s = f.get("source") or {}
            src = (f"{s.get('record')} `{s.get('field_path')}` record date {s.get('record_date') or 'n/a'}, retrieved {s.get('retrieved_at')}"
                   if s else f"guessed from {', '.join(f.get('basis', []))}: {f.get('use')}")
            cv = " **(cannot verify)**" if f.get("cannot_verify") else ""
            L.append(f"| {f['label']} | {f['statement']}{cv} | {src} |")
        L.append("")
    if case.get("alarm"):
        a = case["alarm"]
        L += ["## Cover-gap alarm", "", f"**{a['status']}**: {a['explanation']}", ""]
        for s in a.get("sources", []):
            L.append(f"- {s['record']} `{s['field_path']}` (record date {s.get('record_date') or 'n/a'})")
        L.append("")
    pb = case.get("peer_benchmark")
    if pb and pb.get("total") is not None:
        L += ["## Peer benchmark", "", f"{pb['total']} job posts since {pb['since']} (filter below), retrieved "
              f"{pb['source']['retrieved_at']}. {pb['note']}", "", "| Phrase | Posts | Share |", "|---|---|---|"]
        for p in pb["phrases"]:
            L.append(f"| {p['phrase']} | {p['count'] if p['count'] is not None else 'cannot verify'} | "
                     f"{'' if p['share'] is None else f'{p['share']:.1%}'} |")
        ac = pb["any_cover"]
        L += [f"| **any of these** | {ac['count']} | {'' if ac['share'] is None else f'{ac['share']:.1%}'} |", ""]
        for r in pb.get("by_role", []):
            L.append(f"- {r['role']} (title contains '{r['title_word']}'): {r['total']} posts, {r['with_cover']} mention cover")
        for s in pb.get("samples", []):
            L.append(f"- [{s['company']}, {s['date_added'][:10]}]({s['url']}) `content.description[{s['char_range'][0]}:{s['char_range'][1]}]`: \"…{s['passage']}…\"")
        L += ["", "```json", json.dumps(pb["filter"]), "```", ""]
    if case.get("gaps") is not None:
        L += ["## Gaps (rules.yaml)", ""]
        for g in case["gaps"] or [{"rule_id": "-", "cover": "none", "called_for": "-", "explanation": "no rule fired", "facts_used": []}]:
            L.append(f"- **{g['rule_id']}** {g['cover']}: {g['explanation']} Called for: {g['called_for']}. Facts: {', '.join(g['facts_used'])}")
        L.append("")
    for p in case.get("package") or []:
        L.append(f"- **{p['role']}**: " + "; ".join(f"{i['cover']} ({i['rule_id']}: {i['why']})" for i in p["items"]))
    if case.get("shortlist"):
        L += ["", "## Insurer shortlist (regulator figures only; commission plays no part)", ""]
        for i in case["shortlist"]:
            L.append(f"- **{i['insurer']}** rank {i['rank'] or 'not ranked'}")
            for f in i["figures"]:
                L.append(f"  - {f['metric']}: " + (f"cannot verify ({f['missing']})" if f.get("cannot_verify")
                                                    else f"{f['value']} ({f['period']}) \"{f['source']['passage']}\" {f['source']['url']}"))
    if case.get("workplace"):
        w = case["workplace"]
        L += ["", "## Workplace beliefs (group level)", ""]
        for b in w["beliefs"]:
            L.append(f"- v{b['version']} {b['statement']}: {b['reason'] if b['suppressed'] else b['value']} "
                     f"(n={b['n']}, valid {b['valid_from']} to {b['valid_to'] or 'now'})")
    if case.get("actions"):
        L += ["", "## Actions (wait for the person)", ""]
        for a in case["actions"]:
            L.append(f"- `{a['key']}` **{a['status']}**: {a['summary']}. Reversible: {a['reversible']}. {a['cost_note']}")
    if case.get("questions"):
        L += ["", "## Questions for the person", ""] + [f"- {q['question']} ({q['why']})" for q in case["questions"]]
    if case.get("cannot_verify"):
        L += ["", "## Cannot verify", ""] + [f"- {c['statement']}: missing {c['missing']}" for c in case["cannot_verify"]]
    if case.get("skipped_steps"):
        L += ["", f"Steps reused from the step store after restart: {', '.join(case['skipped_steps'])}"]
    return "\n".join(L) + "\n"
