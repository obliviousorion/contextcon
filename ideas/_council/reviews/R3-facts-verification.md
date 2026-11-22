# R3 Facts and verification

| Idea | Facts | Reason |
|---|---|---|
| 01 AsOf | 5 | Every case is a pure function of dated points; staleness rule; answers fixture-exact. |
| 02 FactGate | 4 | Same verify core, testable; "record date unknown" static fields are loose. |
| 03 Sentinel | 3 | Observations testable; "did headcount fall?" and signals are proxy-shaped. |
| 04 Second Opinion | 2 | Verdict thresholds arbitrary; AGREE from ratio of lower bounds is a wrong fact. |
| 05 Golden Record | 4 | Pairwise merge/no-merge crisp; thin spec, merge reasons unsourced. |
| 08 Same Hands | 2 | Shared-attribute joins testable, but person data and implied-collusion framing risk wrong claims. |
| 17 Raise | 2 | Ranking has no ground truth; retired; lead investor name aliasing (Surge vs Peak XV) showed. |

Fixture spot-checks (sourced/fixtures/live_check/enrich.json, identify_*.json):
- Delhivery 2024-07-15 = 26,656; 2022-06-01 = none (series starts 2022-11-28); ipo 2022-05-24; id 5798; all_domains drl.aero+delhivery.com: CORRECT.
- TCI 2020-01-01 = 418 (2019-12-30); 2026-09-01 = 1,715 (2026-08-31); latest 1,773; 1,773/416 = 4.26x: CORRECT. 2026-10-15 nearest point 2026-09-07 (38 days) so refusal under 14-day rule: CORRECT. Gaps 2022-04-25 to 2022-09-26 and 2026-09-07 to 2026-11-02: CORRECT.
- Shree Balaji: 25 candidates, top 1.0 / 0.8 / 0.8 / 0.6: CORRECT. One headcount point (9, 2026-11-09), year_founded null: CORRECT. Minor: FactGate/brief say revenue bounds "0"; fixture has null (no figure), not 0.
- Delhivery gap claim "2026-09-21 -> 10-05 -> 11-02": only the 10-05 to 11-02 gap exceeds 14 days; fine.
- UNVERIFIED: AsOf's drl.aero identify (only inferred from all_domains); web fetch cost; all KYB/price figures; Second Opinion "~30k vs 35,295 CONTRADICT" threshold is arbitrary (no data basis).

Top idea: AsOf. Biggest wrong-fact risk: stale-but-in-window points presented as true "as of D" (a copy fetched 2026 attesting 2024; weekly points are profile-derived lower bounds, and a late-backfilled history may differ from what was known then). Fix: label every line "stored copy retrieved T, data point dated P"; never use wording "was true on D"; attest only "data point dated P states X"; keep the 14-day max-staleness rule and the drl.aero identify check (0.2 credit) before claiming same-entity.
