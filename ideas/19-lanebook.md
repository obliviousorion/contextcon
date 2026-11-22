# #19 — LaneBook

*(Proposed and reviewed as "#18" on 2026-11-22; renumbered to #19 after a merge collision with a teammate's "Benefits Desk", which claimed #18 first upstream. The five review files under `_council/reviews/19-*-20261122-1543.md` are the judges' verbatim, unedited text and still say "#18" — that was this idea's number when they were written.)*

Back to the [leaderboard](../README.md). Follows [RULES.md](RULES.md).

- **Owner:** Claude (agent), on behalf of the team
- **Created:** 2026-11-22
- **Status:** Dropped (Round 1 score 12/25, below the ≥19-or-beat-lowest-finalist bar; finance and ethics both flagged as the lens's "1" / "2" anchors describe — see §5 reviews below)
- **Parents (if a merge):** none — but reuses AsOf's attest/resolve engine and outbox wholesale (see §13; builder review disputes how much of that actually exists to reuse)
- **Round 1 score:** **12/25** — CS 3 · Novelty 3 · Ethics 2 · Builder 3 · Finance 1 ([reviews](_council/reviews/))
- **Round 2:** not played (did not qualify)

## 0. Round 1 verdict (five-lens review, 2026-11-22 15:43)
Five independent read-only judge sessions, one per lens, per `RULES.md` §5. Full text in [`_council/reviews/18-*-20261122-1543.md`](_council/reviews/).

| Lens | Score | Reason (≤12 words) |
|---|---|---|
| CS | 3/5 | `settle()` is testable; live `trade`/price output is an untestable proxy |
| Ethics | 2/5 | Markets on real carriers' distress proxies; framing risk unresolved |
| Finance | 1/5 | No external buyer; stated cost range is wrong; price unsourced |
| Builder | 3/5 | Buildable, but "wholesale reuse" of an unbuilt AsOf engine is overstated |
| Novelty | 3/5 | Forward-settlement twist is fresh; everything else is AsOf reskinned |

**Fact-check (Finance judge, RULES.md §5.3):** recomputed cost per job from the RULES.md §2 credit table against the idea's own request breakdown. The doc's claimed "≈₹80–150 per contract-month" (§10, as originally written) does not follow from its own 0.2–1.2 + 2–3 + 5-credit components (identify + settle-enrich + one watcher alert ≈ 7.2–9.2 credits ≈ ₹187–239), and omits the cost of `EXTENDED` retry cycles entirely. **Contradicted — the finance figure in §10 below is wrong and should be read as ₹187–239+ per contract, not ₹80–150, until corrected.**

**Why it's dropped, not merged:** Finance's "1" anchor is "unit economics fail, or there's no billable job" — the stated buyer is the 3PL's own treasury desk spending its own budget, not an outside firm paying for a finished job, which fails the problem statement's own "the client pays when the job is done" test. Ethics's "2" documents a framing risk the idea's own §14 already flagged as unresolved (event-contract/stake/trade vocabulary on real counterparties' distress signals reads as a betting pool regardless of sandboxing) and a regression versus Sentinel's pre-action right-of-reply. Builder and Novelty both independently concluded the same thing from different angles: this is substantially AsOf's (unbuilt-as-of-this-review) engine with a pricing skin, not a separable product. All three — Ethics, Builder and Novelty — recommend the same next step: if the team wants the one genuinely new piece (a falsifiable, pre-committed resolution criterion fixed *before* the fact is known, with an `EXTENDED`/`CANNOT VERIFY` state), propose it as a feature of AsOf ("AsOf: Forward Mode") with all trade/stake/price/payout mechanics stripped, rather than as a sibling idea. That is a decision for AsOf's owner under RULES.md §4, not this document.

## 1. One-line pitch
A Kalshi-shaped event-contract desk, but every contract's resolution criterion is a specific dated record, fixed before trading opens — never a guessed probability presented as fact.

## 2. The problem and the paid job
Freight brokers, trade-credit insurers and commodity risk desks are paid today to structure and price hedges on uncertain operational outcomes: will a lane have capacity, will a contracted carrier stay solvent and listed, will a fuel-surcharge index blow a shipment's margin. The mechanism is index-linked freight-forward agreements (the Baltic Exchange model) and parametric trade-credit/weather cover — the broker's fee is a spread or structuring commission on the hedge, charged whether or not the event happens.

For our 3PL: procurement and ops currently absorb this risk with no hedge at all, or informally with a verbal "we think carrier X is fine" — exactly the kind of guess the organizers score against. A firm would pay to convert "we think" into a priced, dated, falsifiable contract.

**Today's price:** freight-derivative and parametric-cover brokerage commissions typically run 1–3% of contract notional. `(ESTIMATE — no sourced India-specific rate card found yet; needs a published freight-derivative or parametric-insurance brokerage quote before this number is used in any finance scoring)`.

## 3. Why it's unique
- **Not a risk score (Sentinel's mistake).** Sentinel was marked down because a verdict built on a headcount lower bound had no ground truth the organizers could test. LaneBook's fix: every contract's resolution criterion names a specific record type and threshold *at creation time, before any trading happens* — so settlement is exactly as testable as AsOf's `attest()`, just forward-dated instead of backward-dated.
- **Not a diligence/KYB tool (AsOf/FactGate).** LaneBook doesn't clear carriers; it prices and settles hedges on dated, falsifiable questions *about* them. It's the same engine, pointed at the future instead of the past.
- **Not a generic exchange.** There are no outside traders and no real money. Markets are auto-generated from the 3PL's own open shipments and vendor book (one tenant, narrow domain, internal desks staking from a capped budget), and every market closes against Crustdata or registry data — never against sentiment, news tone, or a model's guess.
- Other teams building "fact-checkers" or "vendor-risk scores" (the overdone patterns per the leaderboard) don't have a forward-settlement mechanism with a pre-committed, source-typed criterion — that's the part that's ours.

## 4. The service: request types
| Request | Input | Output | Irreversible? |
|---|---|---|---|
| `list_markets(filter?)` | optional filter | open contracts: criterion text, close date, current price | No |
| `open_market(subject, criterion, source_type, close_date)` | entity/subject, a criterion naming a specific record type + threshold, close date | contract id + criterion, or **refused at creation** if the criterion doesn't name a resolvable record type | No to draft; **yes** once a desk stakes real (sandboxed) budget on it |
| `trade(contract_id, side, size)` | yes/no side, stake size | fill price, position, cost against the desk's capped budget | **Yes** — commits budget; holds for approval above a per-trade cap |
| `settle(contract_id)` | triggered at `close_date` | YES / NO from the named dated record with field+passage+date, or **EXTENDED** (record not there yet, new check date) / **CANNOT VERIFY** (extension cap hit → void, stakes returned) | **Yes** — releases a sandboxed payout; held for human approval |
| `audit(contract_id)` | contract id, any time | full evidence chain: criterion as written at open, source link, record date, retrieval date | No |

## 5. Crustdata calls per request
| Request | Endpoint and fields | Credits | Verified? (fixture link or UNVERIFIED) |
|---|---|---|---|
| `open_market` (new subject) | company identify (bind entity by domain, same rule as AsOf — name-only refused) | 0.2 | Verified — same identify behavior AsOf already recorded |
| `open_market` (resolve ambiguous name) | company search, per result | 0.03 × k | Verified — "Shree Balaji Logistics" returns 25 at 0.03 each |
| `trade` | none (internal ledger only — no external call) | 0 | N/A |
| `settle` (company-record criterion) | company enrich — headcount series / revenue-estimate series / public markets (re-pull latest point) | 2 | Verified — same enrich AsOf uses |
| `settle` (web-sourced criterion, e.g. "a filing announces X") | web search + web fetch | 1 + UNVERIFIED (fetch cost not yet measured, per AsOf's open risk) | Partially verified; fetch cost UNVERIFIED |
| close-date trigger | watcher create, `/test`, runs | 0 to create/test; 5 per alert | Verified — same watcher mechanics as AsOf/Sentinel |
| ledger check | account credits/endpoints | 0 | Verified |

No `/batch/*`, contact enrich, employee reviews, social posts, or live professional-network search is used — all disabled on our key.

## 6. Decision rules
- A market can be opened **only** if its criterion names an enabled Crustdata record type or a named public registry/filing field. A criterion like "market sentiment turns negative" is rejected at creation — not just at settlement.
- Pricing is a simple logarithmic market-scoring rule summed across the 3PL's own desks (ops, procurement, finance), each staking from a capped internal budget. The resulting **price is always labeled "aggregated estimate"** in every output — never asserted as a fact, never shown without that label.
- At `close_date`, `settle()` pulls the named record. If a point exists dated on/before `close_date` within the configured staleness window → deterministic YES/NO, citing the exact field and date (same discipline as AsOf's `attest`). If no such point exists yet → **EXTENDED** with a new check date (capped at N, config); if still missing after the cap → **CANNOT VERIFY**, contract voided, stakes returned to all desks.
- Never settle from model memory, a news summary, or sentiment — only the exact field or passage, exactly as AsOf requires for `attest`.
- "Will carrier X default" is refused **at market-open**, before any trading, because no criterion can name a specific court/insolvency record for it — stricter than AsOf, which only refuses this at attestation time.

## 7. Hidden-test cases (at least 4, including duplicate, lookalike and cannot verify)
| Request | Correct answer | Based on (fixture or assumption) |
|---|---|---|
| Market: "Will delhivery.com's headcount fall below 150 by 2026-12-15" | **YES**, citing the enrich point on/before 2026-12-15 if one shows a value under 150; **NO** otherwise — exact figure pulled live, not assumed | AsOf's recorded Delhivery headcount series (Nov 2022 onward, 204 weekly points) |
| Same market, but `close_date` falls inside a known data gap (per AsOf's recorded TCI/Delhivery gaps of up to ~5 months) | **EXTENDED** once (no point within the staleness window), then **CANNOT VERIFY** if still missing after the cap | AsOf's recorded gap data (round2-brief-and-data-check.md) |
| `open_market("Shree Balaji Logistics", ...)` by name only, no domain | **CANNOT RESOLVE** — 25 candidates listed, same as AsOf's `resolve` | AsOf's live check: name-only search returned 25 candidates, top at confidence 1.0 |
| Two `open_market` calls with identical (subject, criterion, close_date) in the same tenant | Second call is a no-op: returns the **existing** contract id, no second market created | Idempotency design, same pattern as AsOf's dedupe key |
| `open_market("carrier X", "will carrier X default", ...)` | **Refused at creation** — no record type can resolve a default/insolvency question; names the missing court/insolvency record type | Same reasoning AsOf and the council applied to Sentinel's rejected risk score |

## 8. Approvals and kill-restart
- Irreversible actions: opening a market with real staked budget, executing a trade above the per-trade cap, releasing a settlement payout.
- Each goes through an **outbox**: intent (action + params) is written with an idempotency key `hash(contract_id, action, nonce)` before any effect runs; on restart, any intent without a recorded effect is replayed exactly once, any intent with a recorded effect is a no-op.
- Settlement payouts run through sandboxed Razorpay/Stripe **test mode only** and are held for human approval before release — never auto-paid.
- `settle()` itself is idempotent: calling it again on an already-settled contract returns the stored verdict, never re-settles or re-pays.
- Same crash gap AsOf closed for watcher create/save applies here for market create/save — closed with the same dedupe-key pattern.

## 9. Ethics
- **No person data.** Contracts resolve only against company-level, dated records (headcount thresholds, listing status, filings) — the same restriction AsOf applies, enforced in `open_market`'s validator, which rejects any criterion referencing a person's employment, health, or other personally identifying outcome.
- **Who could be harmed:** a wrongly-settled contract moves (sandboxed) budget and, if leaked, could misstate a real carrier's status outside the 3PL. Mitigation: all markets and audit trails stay internal to the 3PL tenant; nothing is published externally.
- **Right of reply:** a carrier affected by a settlement (e.g., "headcount fell below threshold") can request the full audit trail and dispute the source record — same evidence-request pattern as AsOf, never an automatic negative action against the carrier.
- **Explanation:** every settlement shows the exact criterion text as written at market-open (before any trading), the source field/passage, and its date — no post-hoc rationalization of why a price moved.
- The **price itself is never shown as a fact or a finding about the carrier** — only the settlement is. This is the load-bearing ethical distinction from Sentinel's rejected design.

## 10. Finance
- **Buyer:** the 3PL's own treasury/ops risk desk (internal budget holder), or — if sold outward — the 3PL's shipping customers wanting to hedge lane risk.
- **Price:** a structuring fee per market opened, plus a spread on trades, mirroring freight-derivative brokerage practice. `(ESTIMATE — needs a sourced India freight-derivative or parametric-cover brokerage rate card; none found yet.)`
- **Measured/computed cost:** creation ≈ 0.2–1.2 credits; settlement ≈ 2–3 credits; a close-date watcher ≈ 5 credits per check — roughly the same per-job range as AsOf (≈ ₹80–150 per contract-month at ≈ ₹26/credit).
- **Sources still needed:** a published freight-derivative or parametric-insurance brokerage commission schedule, and the kickoff kit's real volumes, before any margin figure is presented as more than an estimate.

## 11. Design questions
- **5-minute live fix:** staleness window, extension cap, or adding a new record type are all config changes — same ease as AsOf.
- **100x volume:** the pricing computation (LMSR) is O(1) per trade; the expensive part is the Crustdata `settle()` calls, which reuse AsOf's per-tenant cap/queue design against the enrich rate limit.
- **Second client:** per-tenant market namespace, reusing AsOf's per-tenant key/cache/log pattern directly.

## 12. 3-minute demo script
1. 0:00–0:30 — open a market on a known entity with a criterion tied to a real recorded data point near a chosen close date; show the criterion text and the "aggregated estimate" price label.
2. 0:30–1:10 — move the close date into a known data gap (reusing AsOf's recorded TCI/Delhivery gap): settlement returns **EXTENDED**, not a guess.
3. 1:10–1:40 — attempt `open_market` on "will carrier X default": refused at creation, names the missing record type.
4. 1:40–2:20 — settle a market whose close date has passed: exact field, passage and date cited; approve the sandboxed payout; a judge kills the process mid-payout; restart sends exactly once.
5. 2:20–3:00 — attempt the identical `open_market` call twice: second call returns the same contract id, no duplicate created. Close: "The price is a guess we label as a guess. The settlement never is."

## 13. Build plan and cut-lines
- Reuses AsOf's attest/resolve engine, outbox, idempotency pattern and per-tenant key design wholesale — this is substantially "AsOf's engine, pointed at a forward-dated criterion with a pricing layer on top," built by the same team on the same build day.
- **Build order:** criterion validator (blocks unresolvable markets at creation) → `settle()` reusing `attest()`'s refusal-first logic → outbox/approval wiring → flat-price placeholder for trading → LMSR pricing layer → multi-desk budget split.
- **Cut order:** multi-desk budget split first, then real LMSR pricing (keep a flat/fixed price), then the UI.
- **Never cut:** criterion validation at market-open, `settle()`'s refusal-first logic (EXTENDED/CANNOT VERIFY before any guess), the outbox.

## 14. Open risks and unknowns
1. **Framing risk.** Even sandboxed-money, single-tenant, no-outside-traders, "prediction market" framing may read to the ethics judge as gambling/market-making regardless of safeguards — needs an explicit team discussion before this is built, not just a design mitigation.
2. **Thin buyer evidence.** No sourced brokerage rate card yet for this exact niche in India — the ₹ figures above are estimates until sourced.
3. **Novelty overlap.** A novelty judge may read this as "AsOf with a sportsbook skin" since it reuses AsOf's engine almost entirely — needs a sharp verbal differentiation (forward-committed sourced resolution vs. backward-looking attestation) going into Round 1 review.
4. **Demo risk.** If every open market is still pending at demo time, there's nothing to settle live — needs at least one market whose `close_date` is deliberately set in the past against a known fixture, so `settle()` fires live on stage.
5. Not yet run through Round 1 review (CS / Ethics / Finance / Builder / Novelty) per `ideas/RULES.md` §5 — no live Crustdata calls have been made for this idea; all credit figures above reuse AsOf's already-recorded fixtures (0 new credits spent).

## Discussion
<!-- Others append below: "- <name>, <date>: <proposal>". The owner merges. -->
