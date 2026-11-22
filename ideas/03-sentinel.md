# #3 — Sentinel: "Evidence that you knew" (Receivables Sentinel + Carrier Pulse + LaneWatch)

Back to the [leaderboard](../README.md). Rupee fee figures are unsourced agent estimates unless stated.

- Pool idea #13: Round 1 (max 25): **18** — CS 3 · Novelty 3 · Ethics 3 · Builder 4 · Finance 5
- Pool idea #1: Round 1 (max 25): **16** — CS 3 · Novelty 3 · Ethics 3 · Builder 3 · Finance 4
- Pool idea #2: Round 1 (max 25): **16** — CS 3 · Novelty 3 · Ethics 3 · Builder 3 · Finance 4
- Round 2 head-to-head: **2 of 9** matchups won (beat Second Opinion on the CS and novelty cards).

## Original idea (round 1 pool entry)

Receivables Sentinel: the 3PL CFO/credit-control head's customer credit-distress watch. Headcount decline + hiring freeze + layoff news as leading indicators of non-payment; output "hold / watch / extend credit" (never a default prediction, "risk indicator, not a finding"). company/identify + company/enrich (headcount.timeseries, by_role_absolute, revenue) + job/search + watch webhooks (free /test) + web search/fetch for exact passages. Est. Rs 1,500-5,000 per customer review or Rs 50k-1.5L/month per 100-shipper book vs credit-bureau reports and bad-debt loss. Tests: 30% headcount drop in 90 days => tighten credit with dated field; group firm vs subsidiary kept separate; "will X default?" => cannot verify naming the missing court/insolvency record. Approval gates: cutting credit limit, pausing dispatch, dunning email. Rules in YAML => easy live fix; second client = tenant config. Risk: proxy signal, headcount lower bound.

Carrier Pulse (client-first): monthly carrier/supplier distress watchlist, RAG status per carrier from headcount.timeseries + job/search freeze + web news (insolvency/NCLT) + watch. Est. buyer value Rs 15-60k/counterparty/yr. Tests: -25% headcount => AMBER; lookalike "Express" carriers resolved by domain else cannot verify; insolvency rumour with no fetched page => cannot verify. Risk: headcount is a lower bound.

LaneWatch (surface): same family. Dated Hold/Continue verdict "is carrier operationally healthy as of date X"; headcount slope + job-posting freeze + senior departures (person/search) + news + watcher trigger with free /test. Est. Rs 15-30k per carrier report or Rs 40-80k/month retainer. Risk: sparse series => many cannot verify.

## Council notes
- Round 1: Finance 5 (clearest CFO buyer; bad-debt loss anchors the price), Builder 4 (picked it #1 to ship).
- CS + Ethics objections: a 'hold credit' verdict on a lower-bound proxy has no ground truth the organizers can test; a false positive cuts a real customer's credit.
- Round 2 (as the Sentinel family): won 2 of 9 matchups; redesigned to report only dated observations. Its alert dedupe key was absorbed into the champion.
- CS: headcount is a lower bound; many AMBER guesses; testable only with planted fixtures.
- Novelty: monitoring is fresh but still 'check vendor' shaped; reframe as 'evidence that you knew'.
- Ethics: company-level data, but a RAG status on a lower-bound proxy can harm carriers.
- Finance: ~7 credits ≈ ₹185 per carrier; ₹15–60k/yr claim looks 5–10x inflated vs bureau reports.
- Merged into the Sentinel family (see 03-sentinel.md).
- CS: near-duplicate of Carrier Pulse; sparse series produce mass cannot-verify.
- Ethics: dated verdict is good; 'senior departures' tracks named individuals.
- Finance: ~9 credits ≈ ₹240 per report; per-report price plausible.
- Builder: person/search and person-watch unverified.
- Merged into the Sentinel family (see 03-sentinel.md).

## Round 2 champion pitch (verbatim, written by an Opus champion agent)

# Sentinel: "Evidence That You Knew"

**Pitch:** Watchers on the 3PL's customers and carriers turn each change into a dated, sourced record ("headcount 18,626 on 2022-11-28 -> 35,295 on 2026-11-16"). The system only reports observations. Holds and suspensions stay human decisions, and the counterparty gets a right of reply first.

**Job, buyer, price.** Buyer: the CFO or credit-control head (customers) and the procurement head (carriers). Job = one Signal Record: alert 5 + enrich 2 + web search 1 = **8 credits = Rs 208**. Onboarding: identify 0.2 + enrich 2 = **Rs 57**. Price (ESTIMATE): Rs 1,500/month per counterparty. Not sourced yet; to check against credit-bureau company-report rates (CRIF, D&B India) and the kit's bad-debt figures.

**Request types.**
- `observe(entity, field, D1, D2)`: values at the nearest weekly points on or before each date. A date outside the series = cannot verify.
- `resolve(name|domain)`: one ID, or cannot verify plus the candidate list.
- "Will X default?": always cannot verify, naming what is missing (NCLT/court filing, payment ledger).
- `signal_record(alert)`: an evidence pack plus a held reply draft.

**Calls.** company/identify (domain first) · company/enrich (basic_info, headcount.timeseries, revenue.estimated) · company/search + autocomplete (lookalikes) · job/search (hiring freeze) · web search/fetch (an exact passage or nothing) · watch create / test / runs.

**Hidden tests.**
1. TCI Express 2019-10-28 vs 2026-11-02 -> 416 -> 1,773, both dates cited. Delhivery 2021 -> **cannot verify** (series starts 2022-11-28).
2. Bare name "Shree Balaji Logistics" -> 25 candidates -> **cannot verify**, no watch.
3. shreebalajigrp.com, "did headcount fall?" -> **cannot verify** (one point: 9 on 2026-11-09).
4. Kit lists delhivery.com and drl.aero -> one ID (5798), one watch, one action. "Will Delhivery default?" -> **cannot verify**.

**Watchers.** Each resolved ID gets a watch. `/test` is free and fires a real payload. The webhook writes key `sha(watch_id, company_id, field, signal_date)` into an SQLite action queue, so a duplicate delivery is a no-op. On restart we reconcile through `watch runs` (free).

**Approval + kill-restart.** States: observed -> record_written -> reply_held -> approved -> sent (sandbox), each via `actions.execute(key)`. A kill between any two states resumes from the effects log: no duplicate sends, no double-counted credits. Approval is double-click safe.

**Ethics.** No risk score. Headcount is labelled "lower bound; excludes drivers/contract staff". No automatic credit cut or suspension. A falling signal produces a held "please confirm" note, and a human decides after the reply. Company records only; no person data.

**Build (3h).** 14:15 resolve/observe + trap rules · 15:15 watch + webhook + queue · 16:00 approvals, timeline UI, cost tab · 16:45 eval cases. Cut order: job/search, then web fetch, then revenue. Never cut: resolve, observe, queue, ledger, eval.

**Demo (3 min).** 0:00 Kit loads; the Delhivery duplicate collapses; Shree Balaji = cannot verify. 0:40 TCI's 7-year series next to the small carrier's single point. 1:20 "Will Delhivery default?" -> cannot verify with missing items. 1:50 watch test -> Signal Record -> held reply; kill, restart, approve, sent once. 2:40 Cost: Rs 208/job.

**Attack:** "A headcount chart with a watcher. Where's the value if you never call risk?"
**Rebuttal:** Collections and carrier disputes are fought over what was knowable on a given date, and an unfalsifiable score loses them. A timestamped, sourced, cannot-verify-aware record wins them, and it is the only design hidden tests can grade exactly.

