# Sourced — project export (Hiring Desk)

AI hiring desk: takes a role brief, sources candidates, verifies every CV/profile claim
against the live record, flags lookalikes and duplicates instead of merging them, ranks a
shortlist, and only drafts outreach or books a call once a human approves it.

- `claude/` : the project docs, verbatim, same paths as in a Claude project.
- `SPEC.md` : copy of `claude/SPEC.md` at repo root (agents read it from there; also works
  as AGENTS.md: `cp SPEC.md AGENTS.md`).
- `eval/cases.json` : eval cases extracted from `claude/eval-cases.md` — both the
  shortlist-quality set and the verification-accuracy set. Names in the verification set
  are fictional placeholders; replace with real researched cases before build day, the
  same way the Raise export's own checklist called for real eval companies.

Local Claude Code: unzip into your repo root, then start each agent with the prompts in
`claude/agent-prompts-and-premortem.md`.
Local Claude project: upload the files in `claude/` as project knowledge.

This export has no custom instructions set, and unlike the Raise export it has not been
council-reviewed or judge-simulated — treat the risk register in
`agent-prompts-and-premortem.md` as a first pass, not a verified one.
