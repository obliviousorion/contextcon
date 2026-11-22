TASK: AsOf README, architecture diagram and demo script. Allowed: README.md and docs/ only (do NOT edit docs/START_HERE.md).
Read SPEC.md, ../ideas/01-asof.md (business case §8, demo §9), council/README.md, and the test and ledger output the lead pasted below (if none was pasted, write placeholders marked TODO(lead) for every number).
1. README.md, following the Handbook's "What we want to hear":
   - the job and who pays today; the input; the finished result;
   - the pass mark (hidden-case tests and the chaos test);
   - every data source called, with its credit price;
   - where a person approves;
   - the ledger and the measured cost per job in credits and ₹;
   - run from a fresh clone: uv sync, the replay demo, MCP setup with `claude mcp add`;
   - approaches weighed (see ../README.md leaderboard), what worked and what didn't, the hardest case, who it could get wrong and how it guards against that, what's next.
2. docs/architecture.md: a mermaid diagram showing the MCP / CLI layers, pipeline, engine, crust client (cache, limiter, ledger), outbox and approvals, run state, watchers and the sandbox, with where retries, approvals and the ledger sit.
3. docs/demo.md: the 2-minute script from SPEC §10 with exact commands, plus a backup replay path.
