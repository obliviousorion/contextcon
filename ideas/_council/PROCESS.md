# How the ideas were chosen (22 Nov 2026, ~13:25–14:40)

## Round 1 — ideation + 5-judge council (Sonnet agents)
1. Five ideation agents in parallel, each with a lens: Crustdata surface exploiter · client-first (3PL) · MCP/agent infrastructure · rubric maximizer · contrarian. Each produced 3 ideas → 15 ideas ([round1-idea-pool.md](round1-idea-pool.md)).
2. Five judges scored all 15 (1–5 each, max 25): CS (live run, robustness, design, hidden tests) · Ethics · Finance · Skeptical builder (ship by 17:00?) · Novelty/story.

## Live data check (14:00, 6.6 credits; ledger matched the account balance drop exactly)
Run through our own client in record mode so every response is cached for free replay. Findings: [round2-brief-and-data-check.md](round2-brief-and-data-check.md).

## Round 2 — champions + head-to-head (Opus agents)
1. Four champions each built the strongest version of one finalist (As-Of, FactGate, Sentinel, Second Opinion), with watchers and maximum meaningful Crustdata coverage, and pre-empted attacks. Pitches are embedded verbatim in each idea's document.
2. Three judges played all 6 pairwise matchups each (18 matchups): CS & robustness (also fact-checked pitches against recorded fixtures) · Ethics & finance · Novelty & buildability.
3. Result: AsOf 8/9 · FactGate 7/9 · Sentinel 2/9 · Second Opinion 1/9. Two of three judges ranked AsOf #1; the ethics+finance judge ranked FactGate #1. The champion is a merge (see [../01-asof.md](../01-asof.md)).

## Errors the council caught in the pitches
- Second Opinion marked "TCI grew 4x" AGREE from a ratio of two lower-bound counts — a wrong answer.
- Sentinel claimed headcount "excludes drivers/contract staff" — an unsourced claim about Crustdata's methodology.
- All four assumed drl.aero → Delhivery id 5798 without ever calling identify on it.
- None handled gaps in the weekly series (up to ~5 months) → max-staleness rule added.
