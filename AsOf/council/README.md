# AsOf council: how the lead runs a review

1. Pick a timestamp: `TS=$(date +%H%M)`.
2. Start all five reviewers **in parallel**, in one message, with the same TS: `council-facts`, `council-robustness`, `council-contracts`, `council-e2e`, `council-safety`. Each writes exactly one file, `council/reports/$TS-council-<name>.md`, starting with `VERDICT: PASS|FAIL|BLOCKED`.
3. Gate: `python council/gate.py council/reports $TS` writes `council/reports/$TS-GATE.md` and exits 0 (merge allowed) or 1 (blocked). Findings are routed to the owner agent by file path. Use `--allow-blocked` early on, when some modules don't exist yet.
4. On FAIL: send each owner agent its fix list from the GATE file, then re-run only the reviewers that failed.

Chaos harness: `python council/chaos_kill.py --cmd "<command>" --effects state/effects.jsonl --rounds 5 --expect-keys N [--seed S]`. It kills the process with SIGKILL at random moments, re-runs it, then checks that no action key appears twice and that N distinct actions happened.

Optional: if you'd rather spend Antigravity quota than Claude tokens, the same reviews can run through `agy --print --mode plan`. The older runner is `../docs/council/run-council.sh`; its prompts there are written for the Sourced plan and would need updating for AsOf.
