# Antigravity lane (non-sensitive builds)

The lead sends **non-sensitive** build tasks to Antigravity (`agy`, a separate quota) to save Claude tokens. Everything sensitive stays with the Claude subagents.

| Goes to Antigravity (`agy/tasks/`) | Stays with Claude (`.claude/agents/`) |
|---|---|
| `ui.md`: the web UI in `frontend/`, built against fixtures | the engine: attestation rules, refusals, audit verdicts |
| `docs.md`: README, architecture diagram, demo script | the platform: outbox and exactly-once, resume, limits, ledger, watchers, MCP |
| future: slides or visuals, extra UI screens, copy edits | the pipeline: resolution, case files, anything calling Crustdata |
| | anything touching `.env`, credits, live API calls, `models.py` or `config.yaml` |
| | all council reviews and the gate |

**How to run one** (from `AsOf/`, in the background so the lead keeps working):

```bash
AGY_ALLOW_CMDS="npm,npx,node" agy/run_task.sh agy/tasks/ui.md frontend/
agy/run_task.sh agy/tasks/docs.md README.md docs/
```

- The script prepends `agy/RULES_FOR_AGY.md` (allowed paths only, never `.env`, no paid calls, no git commits, no invented numbers).
- It runs `agy --mode accept-edits --print=<prompt>` and writes a log to `agy/logs/`.
- It then **checks that only the allowed paths changed**:
  - exit 0: OK;
  - exit 2: agy missing or failed, so fall back to the Claude subagent (`asof-docs`, or a general one for the UI);
  - exit 3: files outside the allowed paths changed. The lead reviews them; nothing is auto-reverted.
- The lead reviews the diff and commits. Antigravity never commits.

**First-time setup:** run `agy` once interactively to sign in. Check with `agy --version`.

**Permissions:** headless agy can't prompt, so any unapproved tool is auto-denied (and agy still exits 0). The runner passes a per-session `--settings` that grants `write_file` on the allowed paths only, plus the command prefixes in `AGY_ALLOW_CMDS`. `AGY_SKIP_PERMISSIONS=1` switches to `--dangerously-skip-permissions`; use it only with the user's explicit OK, since agy can then run any command.
