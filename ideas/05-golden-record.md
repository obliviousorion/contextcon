# #5 — Golden Record (master-data dedupe desk)

Back to the [leaderboard](../README.md). Rupee fee figures are unsourced agent estimates unless stated.

- Pool idea #14: Round 1 (max 25): **19** — CS 5 · Novelty 4 · Ethics 4 · Builder 5 · Finance 1

## Original idea (round 1 pool entry)

Master-Data Golden Record desk: dedupe/entity-resolution for the 3PL's customer and carrier master data; explicit merge / no-merge / cannot_verify verdict per pair, never silently merged. company/identify (name+domain), company/search + autocomplete, company/enrich (all_domains, year_founded, all_office_addresses), web/fetch tie-break. Est. Rs 5-20 per record or Rs 50k-2L per 10,000-row clean-up. Tests: same-domain name variants => merge; same name different city/founding year => no merge with reason; bare name no domain => cannot_verify. Merges/deletes in client master are irreversible => approval + idempotent on pair-hash. Risk: may read as "vendor check by another name"; thin personal-data story.

## Council notes
- CS 5: pairwise merge/no-merge verdicts have crisp ground truth; the hidden set is duplicates and lookalikes.
- Builder 5: identify/enrich only; easiest to test.
- Finance 1: unit economics fail alone (~₹53 of enrich per record vs a ₹5–20 price).
- Absorbed into the champion as its entity-resolution step (resolve by domain/id, never by name).
