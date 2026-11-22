# #1 — AsOf (current champion)

> **"Crustdata gives you raw data. AsOf decides what it can swear to — and as of when."**

**Status:** champion after 2 council rounds (not being built yet; team discussion first).
**Scores:** Round 1 (5 judges, max 25): **22** — CS 4 · Novelty 5 · Ethics 5 · Builder 4 · Finance 4 (highest of 15 ideas).
Round 2 head-to-head (3 Opus judges × 3 matchups each): **8 of 9 matchups won** (lost only AsOf-vs-FactGate on the ethics+finance judge's card).
**What it is:** a merge. AsOf's engine and name + FactGate's MCP-gateway delivery and "carrier cleared" lead job + Sentinel's watcher design and alert dedupe + a light, deterministic version of Second Opinion's claim audit.
Source pitches: [round-2 champion pitch](#appendix-a--round-2-champion-pitch-verbatim) below; competing pitches live in [02-factgate.md](02-factgate.md), [03-sentinel.md](03-sentinel.md), [04-second-opinion.md](04-second-opinion.md).

---

## 1. The problem
A 3PL hands freight to dozens of carriers and sub-contractors, many small, many with near-identical names. Two questions keep coming up:
1. **Before work starts:** is this carrier real, and what it says it is? (Procurement pays KYB vendors / analysts for this today.)
2. **After something goes wrong** (cargo loss, SLA dispute, an insurer asking whether the 3PL exercised reasonable care): *what could you actually have known about that carrier on the date you picked it?*

Today both answers are a folder of screenshots and guesses, and a confident wrong answer is the worst outcome — which is exactly how the organizers score (a wrong answer counts against a team more than "cannot verify").
Crustdata's records are stored copies with **dated weekly history**, so they are the right raw material — but raw data answers too eagerly. In our live check the name "Shree Balaji Logistics" returned **25 candidate companies**, the top one at confidence 1.0. AsOf is the layer that refuses to guess.

## 2. The service (request types — each is an MCP tool, a CLI command and a UI action)
| Request | What it does |
|---|---|
| `resolve(name \| domain)` | free autocomplete → company search to narrow → identify **by domain only**. More than one candidate and no domain → **CANNOT RESOLVE**, listing the candidates. Domain aliases (`all_domains`) collapse to one entity id. |
| **`clear_carrier(domain)`** — lead paid job | a clearance file as of today: existence, founding year, listing status, a profile-derived headcount point, revenue band (labelled estimate), corroborating dated web passages. Issuing the clearance is **held for approval**. |
| `attest(entity, field, as_of=D)` | the core: attests only what a dated data point **on or before D** states; otherwise **CANNOT ATTEST** naming what is missing. |
| `observe(entity, field, D1, D2)` | reports both dated values side by side. **Never** derives a growth verdict from lower-bound counts (the council caught this error in Second Opinion's pitch). |
| `audit_claims([...])` | grades structured claims (e.g. lines from a carrier's capability deck) through `attest`. No live LLM document-splitter, so it stays deterministic and restart-safe. |
| `watch(entity)` | creates a Crustdata watcher; each alert re-attests "today", stores a hashed snapshot, and marks affected facts STALE; re-clearance waits for a human. |

**Second product:** the **dated dispute file** — `attest` output for a past date, packaged for an insurer or arbitrator.

## 3. Attestation rules (deterministic, tested against recorded fixtures, all thresholds in config)
- Use the **latest data point on or before D**, never one after it.
- **Maximum staleness:** if that point is more than 14 days (config) before D → CANNOT ATTEST. Added by the round-2 CS judge: real series have gaps of up to ~5 months (TCI has no points between 2026-09-07 and 2026-11-02, and between 2022-04-25 and 2022-09-26; Delhivery jumps 2026-09-21 → 10-05 → 11-02).
- Current-only fields (e.g. domains) are labelled "true at retrieval only".
- Evidence dated after D goes in a separate **"subsequent events"** section and is never attested.
- Headcount is labelled "profile-derived count". We do not claim what Crustdata does or does not count (the ethics judge flagged that as an unsourced claim).
- Any field outside the known record types → "**CANNOT ATTEST: no record type**", never a guess. This is the safety net for whatever the kickoff kit asks.
- Small carrier with no history → a **held evidence request** (domain, GSTIN, registration documents) labelled "*not a negative finding*". Never auto-rejected.
- "Will this carrier default?" → always CANNOT ATTEST, naming the missing court / insolvency record.

## 4. Hidden-test cases (numbers verified by the CS judge against our recorded responses)
| Request | Correct answer |
|---|---|
| Delhivery headcount as of 2024-07-15 | **26,656** (that weekly point exists); founded 2011; IPO 2022-05-24 |
| Delhivery headcount as of 2022-06-01 | **CANNOT ATTEST** — series starts 2022-11-28 (existence and listing still attested) |
| TCI Express headcount as of 2020-01-01 | **418** (2019-12-30 point) |
| TCI Express headcount as of 2026-09-01 | **1,715** (2026-08-31 point), never the latest 1,773 |
| TCI Express as of a date inside a gap (e.g. 2026-10-15) | **CANNOT ATTEST** (nearest point > 14 days old) |
| "Shree Balaji Logistics", no domain | **CANNOT RESOLVE** — 25 candidates |
| Shree Balaji (shreebalajigrp.com), any date before 2026-11-09 | **CANNOT ATTEST** — only one point (9 on 2026-11-09) |
| delhivery.com vs drl.aero | same entity (id 5798) — **UNVERIFIED**: identify was never called on drl.aero; inferred from `all_domains`. 0.2-credit check needed. |

## 5. Crustdata surface used
| Used | For |
|---|---|
| Autocomplete (free), company search, company identify | resolution; making the lookalike problem visible |
| Company enrich — basic_info, headcount time series, revenue-estimate series, public markets | dated attestation |
| Web search live + web fetch | dated, quoted corroboration (quote from the fetched page, never the snippet) |
| Watchers — create, `/test` (free), runs | contemporaneous evidence; fact expiry (STALE) |
| Account credits + endpoints (free) | ledger reconciliation; startup permission check |
| **Crustdata's own MCP** | the demo contrast; AsOf is the policy layer on top |
Deliberately not used: person search/enrich (avoids personal data); job search (our request body got HTTP 400 — could return as an "operating activity" signal once fixed); batch, social-post, contact endpoints (disabled on our key).

## 6. Robustness, approvals, design questions
- Irreversible actions — issue a clearance/dispute file, send an evidence request (sandbox only), create a paid watcher, exceed the spend cap — go through an **outbox**: intent written before effect, idempotency key, exactly-once after a kill.
- Watcher create/save crash gap closed with Sentinel's dedupe key `sha(watch_id, company_id, field, signal_date)`: a duplicate watcher or delivery is a no-op (worst case 5 credits).
- Resume replays from cache with zero new spend (already built and tested in the existing Crustdata client: 17 tests).
- **Second client / 100x:** per-tenant key, cap, cache and log; a queue in front of the 15-RPM enrich limit. Batch endpoints are disabled on our key — say so honestly.
- **5-minute live fix:** rules live in config (e.g. change the staleness window, add a record type, add a refusal rule).

## 7. Ethics
Company data only (no person data). Every refusal names what is missing. No auto-rejection; STALE never suspends a carrier. Carriers get a right of reply via the evidence request. Estimates and profile-derived counts always labelled. Releasing a file outside the client always needs a person.

## 8. Finance
- **Buyer:** procurement / vendor-onboarding head. **Price:** ₹600 per *cleared* carrier; refusals billed at cost or free (a firm won't pay ₹600 for a refusal).
- **Measured cost:** ~3.2–4.2 credits ≈ ₹85–110 per file (≈ ₹26/credit at $0.30/credit × ₹88/USD) → ~80% gross margin. The ledger matched the Crustdata balance drop exactly in today's check (6.6 credits), so it can be shown live.
- Watcher alerts (5 credits each) capped at 2 per carrier per month (₹260), passed through at cost.
- **Second product price:** dispute file ~₹2,500 — unsupported until backed by IRDAI surveyor / loss-assessor fee quotes.
- **Sources still needed:** published KYB quotes (IDfy, Signzy, Perfios/Karza) and the MCA21 fee schedule for the comparison price; the kit's carrier volumes; one measured web fetch for its credit cost.

## 9. Demo (3 minutes)
1. 0:00–0:35 — Claude Desktop: the raw Crustdata MCP is asked about "Shree Balaji Logistics" and confidently picks one; AsOf answers "25 candidates, need a domain". **Must be a real recorded run.**
2. 0:35–1:15 — `clear_carrier` on Delhivery: five dated, sourced lines; ledger shows the rupee cost.
3. 1:15–1:45 — move the date: TCI 2020 attested from its 2019 point; Delhivery 2022-06 flips to CANNOT ATTEST.
4. 1:45–2:30 — approve issuing the file; a judge kills the process mid-send; restart; sent exactly once, no re-spend.
5. 2:30–3:00 — watcher `/test` fires, snapshot hashed, a fact goes STALE. Close: "Next year's dispute cites this."

## 10. Build plan (when we decide to build; ~2.5 hours)
| Who | What |
|---|---|
| B — engine | pure attest/refusal rules incl. staleness, a test for every case in §4, run against `sourced/fixtures/live_check/` (strongest model) |
| A — platform | FastMCP server over the existing client; outbox + approvals; kill-restart test; watchers (create, `/test`, poll runs — no tunnel needed) |
| D — pipeline | resolver, `clear_carrier`, `audit_claims` adapter, kickoff-kit adapter |
| C — UI (Antigravity) | first to cut |
**Cut order:** UI → corroborate → `audit_claims` → revenue. **Never cut:** resolve, attest, outbox, ledger, watcher `/test`.

## 11. Open risks
1. **Kickoff kit unknown.** Any question outside basic_info / headcount / revenue can only go through `corroborate` (web search+fetch) — the least-built piece. Fallback: "CANNOT ATTEST: no record type".
2. **Thin-looking demo** if most answers are refusals — mitigated by the five-line Delhivery file and the TCI 2019 history.
3. **Buyer relevance** (ethics+finance judge): few cargo disputes turn on headcount → lead with carrier clearance, keep the dispute file as the second product.
4. `drl.aero` alias and web-fetch cost unverified (≈1.5 credits to check).

## 12. Council feedback that shaped this design
- Round 1 CS judge: headcount "risk" scores have no ground truth → AsOf attests facts, never risk.
- Round 1 novelty judge: "Everyone else shows what they know; this one shows what it will not claim."
- Round 2 novelty judge: merge into one engine named AsOf, delivered as an MCP gateway in front of Crustdata's own MCP.
- Round 2 ethics+finance judge: lead with "vendor cleared, with the evidence on file" (an example the problem statement itself gives); evidence requests instead of exclusion; price per cleared dossier.
- Round 2 CS judge: max-staleness rule; "no record type" fallback; steal Sentinel's alert dedupe key, FactGate's tenant keys, Second Opinion's right-to-reply line.

---

## Appendix A — round-2 champion pitch (verbatim)

# As-Of: dated counterparty attestations (champion)

**Pitch:** When a cargo loss or SLA dispute lands, As-Of states exactly what the records prove about the carrier *as of the incident date*. Each line names its field, its data-point date and when we retrieved it. Anything it can't prove comes back as "cannot attest: <missing record>".

**Paid job / buyer / price.** The buyer is the 3PL's claims and vendor-risk head. The job is one attestation file per disputed shipment or carrier onboarding. Cost per file is identify 0.2 + enrich 2 + web search 1 (+ fetch, price unverified), about 3.2-4.2 credits, roughly **Rs 85-110**. Fee is **Rs 2,500/file (ESTIMATE)**. Watch add-on is **Rs 750/carrier/month (ESTIMATE)**, capped at 2 alerts (10 cr = Rs 260). To back the fees we need the claim counts and values in the kickoff kit, plus published KYB/vendor-verification price lists. The idea pool's Rs 1,500-4,000 KYB figure is unsourced.

**Service: 4 request types** (MCP tools, with the same calls exposed in the CLI and web UI)
1. `resolve(name|domain)`: autocomplete (free) gives candidates. If no domain is given, company/search (India, logistics, 0.03/result) narrows them. company/identify **by domain** then binds the crustdata id. A name alone never binds.
2. `attest(entity_id, field, as_of)`: company/enrich (basic_info, headcount, revenue). We return the latest weekly point **on or before D**, never interpolated and labelled "lower bound". `existed` uses year_founded (attested only for D ≥ 1 Jan of founded+1). `listed` uses ipo_date ≤ D. Revenue is returned only as "Crustdata *estimate* band". Current-only fields (all_domains, name) come back as "true at retrieval T; cannot attest as of D".
3. `corroborate(entity_id, claim, as_of)`: web search, then fetch. We need an exact passage on a page dated ≤ D. Anything dated after D goes into a separate "subsequent events" section and is never attested.
4. `watch(entity_id)`: watcher create, with /test free. Every alert re-runs `attest(..., as_of=today)` and stores a hashed snapshot, so the record of what we knew and when builds itself. Next year's dispute can then cite *contemporaneous* evidence.

**Hidden tests (correct answers)**
- delhivery.com and drl.aero appear as separate kit rows. Both resolve to id 5798 (all_domains), giving one file and no double charge.
- Delhivery, D=2022-06-01: existed **ATTESTED** (founded 2011). Listed **ATTESTED** (IPO 2022-05-24). Headcount **CANNOT ATTEST** because the series starts 2022-11-28.
- TCI Express, headcount D=2020-01-01: **ATTESTED** with the 2019-12-30 point, labelled lower bound. This proves the old "no data before Nov 2022" rule is not universal.
- "Shree Balaji Logistics", name only: **CANNOT ATTEST: 25 candidates**. We list the top 4 and ask for a domain or GSTIN. With shreebalajigrp.com: D=2026-06-01 gives **CANNOT ATTEST** (the only point is 2026-11-09). D=2026-11-15 gives **9 (lower bound)**.

**Approval + kill-restart.** Lookups are read-only. Three things are irreversible: *issuing* a signed file to an insurer or arbitrator, creating a paid watcher, and spend above the per-file cap (5 cr). Each one stops in an approval queue. The idempotency key is hash(entity_id, field, as_of, evidence-hash). Stages (resolve, fetch, evaluate, draft, approve, issue, watch) write intent and then result to SQLite. On restart, cached replay makes re-fetches free. The outbox sends each file once by id, and watcher ids are saved before we acknowledge. A crash between create and save is reconciled by a name tag (listing is unverified, so this is a known risk).

**Ethics.** Company-level only, with **zero person enrich**. We attest facts, never fault ("not a finding about the incident"). Every refusal names the missing record. A name alone never binds. Estimates and lower bounds carry their labels. Post-D evidence is kept separate. Each file shows "stored copy retrieved T".

**3-hour build:** core rules as a pure function over recorded enrich JSON, plus tests (0:45). Resolver and MCP server (1:30). Corroborate, approval and outbox (2:15). Watcher and snapshot (2:45). UI (3:00). **Cut order:** UI, then corroborate, then revenue. The CLI plus MCP is enough to demo.

**Demo (3 min)**
- 0:00-0:40: Claude Desktop calls `attest` on Delhivery for D=2024-07-15. The file comes back with existed, listed, headcount at the 2024-07-15 point, revenue band (estimate), and domains (retrieval-only). That's five dated lines.
- 0:40-1:20: the Shree Balaji name gives 25 lookalikes and a refusal. Adding the domain gives 9 (lower bound), and the June date gives a refusal.
- 1:20-2:00: TCI 2020 is attested from the 2019 series. The ledger shows Rs 98 for the file.
- 2:00-2:40: approve the issue, kill it mid-send, restart. It sends exactly once.
- 2:40-3:00: watcher /test fires and a new snapshot appears in the timeline.

**Strongest attack:** "A copy fetched in 2026 can't prove 2024. This is just enrich with a date filter."
**Rebuttal:** We don't claim the world was X. We attest that a dated data point in a named record says X, with its retrieval time and hash, and the strict refusal rules are the product. The watcher fixes the gap going forward: from month one, every alert snapshot is contemporaneous evidence the client owns. The demo also shows five positive lines on a real carrier, not just refusals.

## Discussion
<!-- Others append below: "- <name>, <date>: <proposal>". The owner merges. -->
- Claude (agent), 2026-11-22: [#18 LaneBook](18-lanebook.md) (a Kalshi-shaped event-contract idea) was proposed, five-lens reviewed, and dropped (12/25 — see its §0). Three of five lenses (Ethics, Builder, Novelty) independently converged on the same suggestion, worth your call as owner: strip every trade/stake/price/payout mechanic and consider a narrow **"AsOf: Forward Mode"** feature — `attest(entity, field, as_of=D)` already answers "what did we know as of a past D"; the only genuinely new piece LaneBook surfaced is a **pre-committed criterion fixed before the fact is known**, i.e. "we state today, citing record type R, that field F will say X by future date D" — graded automatically into ATTESTED / NOT ATTESTED / EXTENDED (record not there yet, one retry before CANNOT VERIFY) when D arrives. No staking, no trading, no price, no payout, no desk vocabulary — those were exactly what Ethics (2/5) and Novelty (3/5) flagged as unresolved gambling/defamation-optics risk and reskinning risk respectively. Not merging this — your call under RULES.md §4.


## Appendix B — original round-1 pool entry

As-Of (contrarian): dated diligence affidavit: for a carrier and date D (after a cargo loss/SLA dispute), what can records PROVE about the carrier as of D (existence, size via nearest headcount point on/before D, registered name/domain); refuses when record refreshed after D or D before Nov 2022 ("cannot attest"). Est. Rs 3,000-6,000/file vs disputed claims Rs 2-20 lakh. Risk: sparse series => mostly cannot verify; thin-looking demo.
