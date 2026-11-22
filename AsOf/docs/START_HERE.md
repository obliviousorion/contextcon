# Starting the AsOf build in a new Claude Code session

1. `cd ~/projects/contextcon/AsOf && git pull`
2. Run `claude` from **this folder**, so `CLAUDE.md` and `.claude/agents/` load. Opus is recommended for the lead.
3. Check that the agents loaded: `/agents` should list asof-engine, asof-platform, asof-pipeline, asof-docs and the five council-* reviewers.
4. (Optional, for the demo contrast) add the Crustdata MCP: `claude mcp add --transport http crustdata https://install.crustdata.com/mcp`.
5. Paste this as the first message:

> Read CLAUDE.md, SPEC.md, backend/models.py and config.yaml. Run Phase 0. Then start Phase 1 by launching asof-engine, asof-platform and asof-pipeline in parallel, with precise file-scoped tasks taken from their agent definitions. When they report, integrate (Phase 2) and run the full council (Phase 3) with the gate. Keep everything in replay mode. Ask me before any live Crustdata call or any git push. Give me short status updates at each phase.

The ideas and their history are in `../ideas/` (the champion is `../ideas/01-asof.md`); scoring follows the Handbook rubric in `../docs/builder-handbook.txt`.
