#!/usr/bin/env python3
"""Merge council reports into one gate file. Usage: gate.py <reports_dir> <TS> [--allow-blocked]
Exit 0 = merge allowed, 1 = blocked. Routes findings to module owners by file path."""
import glob, os, re, sys
OWNERS = [("backend/engine", "asof-engine"), ("tests/engine", "asof-engine"),
          ("backend/platform", "asof-platform"), ("backend/crust", "asof-platform"), ("tests/platform", "asof-platform"),
          ("backend/pipeline", "asof-pipeline"), ("backend/cli", "asof-pipeline"), ("tests/pipeline", "asof-pipeline"),
          ("README", "asof-docs"), ("docs/", "asof-docs")]
def owner(path):
    return next((o for pre, o in OWNERS if pre in path), "unassigned (lead)")
rd, ts = sys.argv[1], sys.argv[2]; allow_blocked = "--allow-blocked" in sys.argv
rows, tasks, ok = [], {}, True
files = sorted(f for f in glob.glob(os.path.join(rd, f"{ts}-*.md")) if not f.endswith("GATE.md"))
if not files: print("no reports found"); sys.exit(1)
for f in files:
    name = os.path.basename(f)[len(ts)+1:-3]; txt = open(f, errors="replace").read()
    m = re.search(r"^VERDICT:\s*(PASS|FAIL|BLOCKED)", txt, re.M)
    v = m.group(1) if m else "FAIL(no verdict)"
    if v == "PASS": pass
    elif v == "BLOCKED" and allow_blocked: pass
    else: ok = False
    rows.append((name, v))
    if v != "PASS":
        for ln in txt.splitlines():
            mm = re.match(r"^\s*\d+\.\s*(.*)", ln)
            if mm: tasks.setdefault(owner(mm.group(1)), []).append(f"[{name}] {mm.group(1)}")
        if not any(name in t for ts_ in tasks.values() for t in ts_): tasks.setdefault("unassigned (lead)", []).append(f"[{name}] {v}: read {os.path.basename(f)}")
out = [f"# Council gate {ts}: {'PASS - merge allowed' if ok else 'BLOCKED - do not merge'}", "", "| reviewer | verdict |", "|---|---|"] + [f"| {n} | {v} |" for n, v in rows]
for o, ts_ in sorted(tasks.items()): out += ["", f"## Fix list for {o}"] + [f"- {t}" for t in ts_]
open(os.path.join(rd, f"{ts}-GATE.md"), "w").write("\n".join(out) + "\n"); print("\n".join(out)); sys.exit(0 if ok else 1)
