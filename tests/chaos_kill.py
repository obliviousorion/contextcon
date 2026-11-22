#!/usr/bin/env python3
"""Generic kill-and-restart chaos harness.
Runs CMD, SIGKILLs it after a random delay, reruns it (repeat ROUNDS times), then lets it finish.
The service must append one JSON line {"key": "...", ...} to EFFECTS for every irreversible action.
PASS = final run exits 0 AND no key appears more than once in EFFECTS.
Usage: chaos_kill.py --cmd "python app.py" --effects /path/effects.jsonl [--rounds 5] [--seed 1] [--max-delay 3.0] [--expect-keys N]"""
import argparse, collections, json, os, random, shlex, signal, subprocess, sys, time

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--cmd", required=True); p.add_argument("--effects", required=True)
    p.add_argument("--rounds", type=int, default=5); p.add_argument("--seed", type=int, default=None)
    p.add_argument("--max-delay", type=float, default=3.0); p.add_argument("--timeout", type=float, default=120)
    p.add_argument("--expect-keys", type=int, default=None, help="exact number of distinct effect keys expected after completion")
    a = p.parse_args()
    seed = a.seed if a.seed is not None else random.randrange(10**6); rng = random.Random(seed)
    print(f"seed={seed}")
    for i in range(a.rounds):
        d = rng.uniform(0.05, a.max_delay)
        proc = subprocess.Popen(shlex.split(a.cmd), start_new_session=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        try: proc.wait(timeout=d); state = "finished-before-kill"
        except subprocess.TimeoutExpired:
            os.killpg(proc.pid, signal.SIGKILL); proc.wait(); state = f"killed@{d:.2f}s"
        print(f"round {i+1}: {state}")
    t0 = time.time(); r = subprocess.run(shlex.split(a.cmd), timeout=a.timeout, capture_output=True, text=True)
    print(f"final run exit={r.returncode} in {time.time()-t0:.1f}s")
    keys, bad = [], 0
    if os.path.exists(a.effects):
        for ln in open(a.effects):
            ln = ln.strip()
            if not ln: continue
            try: keys.append(json.loads(ln)["key"])
            except Exception: bad += 1  # torn line from a kill mid-write
    dup = {k: n for k, n in collections.Counter(keys).items() if n > 1}
    problems = []
    if r.returncode != 0: problems.append(f"final run failed (exit {r.returncode}): {r.stderr[-300:]}")
    if dup: problems.append(f"DUPLICATE effects (action ran more than once): {dup}")
    if a.expect_keys is not None and len(set(keys)) != a.expect_keys: problems.append(f"expected {a.expect_keys} distinct effects, got {len(set(keys))} (lost action?)")
    print(f"effects={len(keys)} distinct={len(set(keys))} torn_lines={bad}")
    print("CHAOS: PASS" if not problems else "CHAOS: FAIL\n- " + "\n- ".join(problems))
    sys.exit(0 if not problems else 1)
main()
