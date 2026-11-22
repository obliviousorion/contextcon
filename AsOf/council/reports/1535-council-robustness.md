VERDICT: PASS

FINDINGS: none blocking. The earlier minor items from 1526 are unchanged: ledger torn-tail undercount of at most one call, demo_actions.py key name, and the `uv run` note.

EVIDENCE (HEAD ff4a8c6, MODE=replay):
- `uv run pytest -q tests/platform backend/crust` gave 47 passed.
- Chaos on the real path: a scratch script at /tmp/claude-1000/s/real.py builds an EvidenceRequest, approves it, and calls pipeline.api.issue. It ran with `--rounds 3 --expect-keys 1`.
  - Seed 11 (max-delay 1.5): kills landed after the script finished. effects=1 distinct=1, CHAOS: PASS.
  - Seed 5 (max-delay 0.15): all 3 rounds were killed mid-run at 0.11s, 0.12s and 0.13s. The final run exited 0. effects=1 distinct=1 torn_lines=0, CHAOS: PASS.
- No regression from the MCP kwargs change.

FAILING TESTS: none.
