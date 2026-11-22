# #2 — FactGate (verified-facts MCP gateway)

Back to the [leaderboard](../README.md). Rupee fee figures are unsourced agent estimates unless stated.

- Pool idea #7: Round 1 (max 25): **21** — CS 5 · Novelty 3 · Ethics 5 · Builder 4 · Finance 4
- Round 2 head-to-head: **7 of 9** matchups won (lost to AsOf on the CS and novelty cards; beat AsOf on the ethics+finance card).


## Round 3 (Handbook rubric) — 68/100
Scores E2E·Facts·Robustness·Value·Demo = 3·4·4·3·3 (each 1–5, weighted 25·20·20·20·15). Reviews: [_council/reviews/](_council/reviews/).

Output is tool-shaped and less crisp than a finished file; good approvals and idempotency; static fields labelled 'record date unknown' are loose; the gateway reads as plumbing others build (buyer: bank or NBFC KYB onboarding teams).

## Original idea (round 1 pool entry)

FactGate (MCP/infra): an MCP server any agent calls: verify_fact(subject, field, as_of) returns only {value, exact_passage, url, record_date, cost} or CANNOT_VERIFY{missing}; recheck(fact_id); clear_vendor job (~Rs 600/dossier vs Rs 1,500-4,000 KYB). SQLite ledger, idempotency keys, approvals table. Second client = tenant key. Covers Trust&Compliance + Infrastructure-for-agents tracks. Risk: stored copies often predate question => many cannot verify; MCP tool names unverified.

## Council notes
- Round 1: CS 5 (strict sourced-or-refuse contract matches the rules; tenant key answers 'second client'), Ethics 5, Novelty 3 ('5+ teams will build fact-checkers').
- Round 2: won 7 of 9 head-to-head matchups; the ethics+finance judge ranked it #1 (procurement already pays for KYB; 'vendor cleared, with the evidence on file' is an example in the problem statement).
- Absorbed into the champion: MCP-gateway delivery, carrier-clearance lead job, per-tenant keys/caps/logs, watcher-driven STALE marking, the raw-MCP-vs-gateway demo contrast.
- Weak points flagged: CANNOT_VERIFY silently excludes small carriers (fix: held evidence request, 'not a negative finding'); a firm will not pay ₹600 for a refusal (fix: price per cleared dossier).

## Round 2 champion pitch (verbatim, written by an Opus champion agent)

# FactGate — the provenance firewall for a 3PL's agents

**Pitch:** An MCP gateway that every agent and staff member at the 3PL must send business facts through. A fact comes back with its source field or passage, URL, record date and cost, or as CANNOT_VERIFY naming what is missing. Facts expire when a Crustdata watcher sees the world change.

**Paid job: "Clear a new carrier"** (buyer: the 3PL's procurement or vendor-onboarding head). Calls: autocomplete (free), identify by domain (0.2), enrich basic_info+headcount+revenue (2), web search (1), one web fetch (price not yet measured, budgeted at 1), watcher create (free). That is about 4.2 credits, roughly **Rs 110 per job**, plus Rs 130 for each later watch alert (5 credits). **Price: Rs 600 per dossier (estimate).** The comparison figure of Rs 1,500–4,000 for a manual KYB check is an *estimate* and needs Indian KYB vendor rate cards or a quote from the client's procurement team. Second job, using the same tools: answering a client's question from the kickoff kit ("is carrier X still operating at this size?").

**Request types (MCP tools):** `resolve(name|domain)` returns an entity id or AMBIGUOUS with candidates. `verify_fact(subject, field, as_of)` returns `{value, field_path or passage, url, record_date, cost, fact_id, expires_on_watch}` or `CANNOT_VERIFY{missing}`. `recheck(fact_id)`. `clear_carrier(domain)` builds the dossier and holds it for approval. `budget(tenant)`. `audit(run_id)` replays the log. Each tenant key has its own credit cap, cache and log.

**Exact Crustdata calls:** company/identify, company/enrich, company/search (same-domain and sibling lookalikes), autocomplete, web search live + web fetch (exact passage), watchers create/test/runs. person/search+enrich only for a named signatory in the kit, because personal data is excluded by default. It runs **alongside Crustdata's MCP:** theirs returns raw data, and FactGate is the policy layer on top (it refuses, cites, charges budgets and expires facts). The difference shows in the demo: an agent using raw MCP picks the 1.0 "Shree Balaji", and FactGate refuses.

**Hidden tests (answers from today's live data):**
1. *Duplicate:* verify Delhivery via `drl.aero`, then via `delhivery.com`. Both resolve to id 5798 (`all_domains`), there is one cache entry, and the second call costs 0 credits.
2. *Lookalike:* "Shree Balaji Logistics" given by name only returns 25 candidates (1.0, 0.8, 0.8, 0.6…). Answer: `CANNOT_VERIFY{missing: domain}` with the top candidates listed. FactGate never auto-picks.
3. *Unsettleable:* the shreebalajigrp.com headcount as of 2025-06-01. The only data point is 2026-11-09 (9 employees), so the answer is `CANNOT_VERIFY{missing: headcount point on/before 2025-06-01}`. "Will they default?" also returns CANNOT_VERIFY, with no record type available.
4. *Records after 1 Sep 2026:* TCI Express headcount as of 2026-09-01. FactGate returns the 2026-08-31 weekly point (Monday series) with `record_date=2026-08-31`. It never returns the latest point (1,773 on 2026-11-02). A static field like Delhivery `year_founded=2011` is labelled "record date unknown, latest refresh 2026-11-16".

**Approval + kill-restart:** Irreversible actions (adding the carrier to the master, emailing a client) are held in an approvals table. Each action has an idempotency key `hash(tenant, job, action)` and an effects log. If the process is killed mid-job, the crash-resume we already built replays from the ledger, cached calls cost 0, and the action runs exactly once.

**Watcher integration:** `clear_carrier` creates a company watcher. When an alert or `/test` payload arrives, the facts it touches (headcount, domain) are marked STALE, `recheck` is forced and any dependent dossier is re-held. The demo uses the free `/test`.

**Ethics:** Wrong answers are treated as worse than refusals. FactGate makes no default or solvency predictions. Personal-data lookups are off unless justified and logged. Budgets are hard caps. Everything can be replayed by judges.

**3-hour plan:** 14:15–15:15 MCP server + verify_fact over the existing client/ledger, with as_of nearest-point logic. 15:15–16:00 resolve/lookalike rule + CANNOT_VERIFY. 16:00–16:40 clear_carrier + approvals + idempotency. 16:40–17:00 watcher → STALE. *Cut-lines, in order:* drop web fetch passages, then person tools, then the multi-tenant UI (keep the per-key cap).

**3-min demo:** (0:00) An agent asks the raw Crustdata MCP and confidently gets the wrong Shree Balaji; FactGate refuses. (0:40) Delhivery is cleared with cited fields at Rs ~110. (1:20) The process is killed during approval, restarted, and the action runs once. (2:00) A watcher `/test` marks the headcount stale and recheck runs. (2:30) Tests 1–4 replay from the audit log.

**Strongest attack:** "This is a fact-checker wrapper, and most answers are CANNOT_VERIFY." **Rebuttal:** A checker grades text after the fact. FactGate sits *in front of* the agents, so unsourced facts never get through. Every refusal names exactly what is missing and has a price. Expiry driven by watchers is something no static checker does.

