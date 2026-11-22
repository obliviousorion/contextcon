# #4 — Second Opinion (auditor of another party's deliverable)

Back to the [leaderboard](../README.md). Rupee fee figures are unsourced agent estimates unless stated.

- Pool idea #10: Round 1 (max 25): **18** — CS 3 · Novelty 4 · Ethics 4 · Builder 3 · Finance 4
- Round 2 head-to-head: **1 of 9** matchups won (beat Sentinel on the ethics+finance card).


## Round 3 (Handbook rubric) — 71/100
Scores E2E·Facts·Robustness·Value·Demo = 4·2·3·4·5 (each 1–5, weighted 25·20·20·20·15). Reviews: [_council/reviews/](_council/reviews/).

Demo 5 ('a graded diff reads instantly'); Value 4 (buyer: diligence and credit teams that already buy outside reports). Facts 2: AGREE on 'TCI grew 4x' from a ratio of two lower bounds is a wrong fact, and the CONTRADICT thresholds are arbitrary and not date-matched. Robustness 3: the LLM claim-splitter can break exactly-once after a restart. Fix: structured claims graded by AsOf's attest; no ratios.

## Original idea (round 1 pool entry)

Second Opinion (contrarian): re-verifies every line of ANOTHER firm's carrier-compliance pack: agree/contradict/cannot verify, catches lookalike mix-ups and stale pages (~Rs 1,500-2,500/pack). Risk: close to vendor-check.

## Council notes
- Round 1: Novelty 4 ('auditing another firm's work is inverted and memorable'), Ethics 4, CS 3 (close to vendor-check).
- Round 2: won 1 of 9 matchups. CS judge: its LLM claim splitter can split differently after a restart, so exactly-once breaks. Ethics+finance judge: it marked 'TCI grew 4x' AGREE from a ratio of two lower bounds — a wrong answer about a counterparty; its CONTRADICT thresholds are arbitrary.
- Absorbed into the champion: a deterministic `audit_claims` over structured claims (no live splitter) and the right-to-reply line.

## Round 2 champion pitch (verbatim, written by an Opus champion agent)

# Second Opinion: champion brief

**Pitch:** Any document another party hands the 3PL (a carrier deck, shipper RFP, rival memo, KYB pack, another agent's output) comes back as a graded diff. Each line is AGREE, CONTRADICT or CANNOT VERIFY, with the exact field or passage and its record date.

**Job, buyer, price:**
- Buyer: the procurement or risk head, who pays analysts or KYB firms today.
- Price: Rs 1,500 per pack of up to 15 claims (estimate; back with KYB vendor quotes).
- Cost: identify 0.2 + enrich 2 + lookalike company/search 0.75 + 2 web searches 2, about 5 credits or about Rs 130. Margin is about 90%.
- Extra product, "grade the checker": we score another checker's pack (precision, stale or unsourced lines).

**Requests:** `audit_pack(doc, as_of)`, `reaudit(claim_id)`, `grade_checker`. All three are also exposed as MCP tools.

**Crustdata calls:**
- autocomplete (free): normalise the name.
- identify by domain. Name-only identify gives 25 candidates, so CANNOT VERIFY.
- company/search: the lookalike set to rule out.
- enrich: year_founded, all_domains and ipo_date for identity. Headcount weekly series, nearest point on or before the claim date. Revenue series for range checks only.
- web search + fetch: news and licence passages.
- person search/enrich: only when a claim names a person.
- watchers.

**Hidden tests:**
1. *"Shree Balaji Logistics, est. 2004, 400 staff", no domain:* 25 candidates, so CANNOT VERIFY (missing: domain). With shreebalajigrp.com, both claims are still CANNOT VERIFY: year_founded is null, and the record shows 9 staff on 2026-11-09 but headcount is a lower bound.
2. *"Delhivery ~30k staff":* CONTRADICT, 35,295 on 2026-11-16 (headcount series). "Founded 2011, IPO May 2022" is AGREE (ipo_date 2022-05-24).
3. *"TCI Express grew 4x since 2019":* AGREE, 416 on 2019-10-28 to 1,773 on 2026-11-02 = 4.26x.
4. *Duplicate and unsettleable lines:* lines naming Delhivery and drl.aero both resolve to id 5798 through all_domains, so one verdict, charged once. "98.5% on-time Oct 2026" is CANNOT VERIFY (missing: shipment records).

**Approval and kill-restart:** Contradiction reports, vendor rejections and client emails wait for approval. The idempotency key is hash(pack, claim, call). The cache replays paid calls on restart, so nothing is re-spent, and the executor runs each action exactly once.

**Watchers:** Each AGREE that rests on a changeable fact (headcount, news) gets a watcher (create and test are free). An alert (5 credits) re-audits only the affected claims and shows the flip, e.g. "AGREE (16 Nov) -> CONTRADICT". The notice waits for approval.

**Ethics:** We grade claims, never firms or people. CONTRADICT is not an accusation of fraud. Headcount is always labelled a lower bound. No personal data unless a claim names the person. The counterparty gets a right-to-reply line.

**Build (14:15-17:00):**
- First hour: claim splitter (manual-edit fallback) and resolver.
- Second hour: YAML verdict rules (tolerances, as-of point) and citations.
- Last 45 minutes: watcher re-audit, approvals, grade_checker.
- Cut in this order: grade_checker, MCP wrapper, person calls, revenue.

**Demo (3 min):**
- 0:00: load a deck written by "another vendor's agent".
- 0:30: the Shree Balaji 25-candidate trap.
- 1:15: TCI agree and Delhivery contradict, each with field and date.
- 1:45: kill and restart; the ledger shows no double spend.
- 2:15: watcher /test fires, the line flips, the notice waits for approval.
- 2:45: checker score card.

**Attack:** "Vendor-check or FactGate with extra steps, and it mostly says cannot verify."
**Rebuttal:**
- Vendor-check asks "is X real?". We grade an adversarial document's assertions, spanning four tracks.
- FactGate can be our core; this is the paid job built on it.
- CANNOT VERIFY is the product: the exact list of what the counterparty must prove before money moves.

