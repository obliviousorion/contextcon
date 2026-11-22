# R3 judge: End-to-end execution (25) and Robustness (20)

| Idea | E2E | Robust | Reason |
|---|---|---|---|
| 01 AsOf | 4 | 5 | Dated clearance/dispute file issued after approval; outbox, exactly-once, staleness and CANNOT rules. |
| 02 FactGate | 3 | 4 | Gateway is tool-shaped; clear_carrier finishes, but output is less crisp. Good approvals/idempotency. |
| 03 Sentinel | 3 | 3 | Alert-to-held-reply is complete, but proxy signal and false-positive harm hurt safety. |
| 04 Second Opinion | 4 | 3 | Finished audit report; LLM claim-splitting can break exactly-once on restart. |
| 05 Golden Record | 4 | 4 | Crisp merge/no-merge/cannot_verify verdicts, pair-hash idempotency; messy names handled by design. |
| 08 Same Hands | 3 | 2 | Graph output, no clear finished act; defamation and personal-data exposure. |
| 17 Raise | 3 | 3 | Request-to-held-drafts pipeline is real, but ranking has no correct result; no exactly-once send. |

**Biggest weakness of the top idea (AsOf):** E2E and robustness both lean on the kickoff kit being matched by basic_info/headcount/revenue. The `corroborate` path is the least built, so many real requests end in "CANNOT ATTEST". The result is honest, but it may read as a finished refusal rather than a finished job. Weekly gaps (TCI) add to this.

**Is reconsidered Raise competitive?** Not on these criteria. Its E2E is decent: peers, ranking, conflicts, cited drafts, and an approve step. The citation validator, cache/replay and budget cap are solid. It falls short on robustness: competitor lists were empty for 8 of 15 companies. It uses person search/enrich, which is more personal data than the job needs. It has no outbox or idempotent-send design, and its eval leans on ranking rather than a hidden "correct finished result". It sits behind AsOf and Golden Record here.
