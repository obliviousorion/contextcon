# ContextCon 05: Final Winning Plan (council-reviewed)

**Event:** Sun Nov 22, 9 AM–9 PM, BITS Pilani. Sponsor: Crustdata (YC F24). Theme: "Services, Replaced." Prizes: $12K pool, Crustdata PPIs, and a 1:1 with Jon Xu (YC GP) for the top 3. Format at earlier editions: a working live demo is mandatory ("ship it or it doesn't count"), with about a 3-minute demo and 2 minutes of Q&A.

The council had five members: an API feasibility auditor, a researcher on past editions, a judge simulator, a business and pitch strategist, and a build architect. This doc is the result.

---

## 1. Decision: build **Raise**, an AI fundraising agent for founders

> "In 2010 a YC company replaced the financial advisor with software. BlackRock bought it. Today I'm replacing the fundraising advisor, who charges founders 2–8% of their round."

**What it does, end to end:**
1. **Input:** a startup, as a domain or a one-liner, plus the stage being raised.
2. It finds the startup's real peers (similar companies plus competitors).
3. It pulls their funding rounds with **named lead investors** from Crustdata.
4. **Deterministic rules** rank investors by who actually led rounds in this space, at this stage, recently, in this geography.
5. **Conflict check:** it excludes or flags investors who backed a direct competitor, with the source shown.
6. It finds the **right partner** at each fund, plus **warm-intro paths** from overlapping work history.
7. It drafts outreach that cites real facts, and holds every draft for founder approval.
8. A **watcher** alerts in Slack when a new round happens in the space (new active investors).

**It ends with an action** (approved, cited outreach to a ranked, conflict-checked investor list), not a report. Earlier editions explicitly asked for this: "the accepted offer rather than a list."

### Why Raise instead of the original Associate (VC analyst)
| Finding | Source |
|---|---|
| At least 3 teams at ContextCon 03 (IITB, Oct 31) already shipped a "verify founder → cited IC memo" agent (Deal Desk, Receipts, SignalGate). Judges have seen Associate. | Past-editions research |
| A VC tool gets compared with Harmonic and Specter. Jon Xu is the investor, so a student teaching him sourcing hits his most skeptical spot. | Judge simulation |
| A founder-side tool makes Jon the target user. Helping founders raise is literally what YC does. | Judge simulation |
| Crustdata's company enrich returns `funding.milestones[]` with `investors` and `lead_investors`, and search can filter `funding.investors`, so ground truth exists. | API audit |
| Fundraising consultants charge $3K–$25K a month or a 2–8% success fee (the source sells this service, so it may be biased). Founders far outnumber funds. | Business research |

Estimated top-3 odds from the judge simulation: Associate as-is ~12–15%, **Raise with live eval ~25–30%**. These are rough judgement calls, not measurements.

---

## 2. The five things that make Raise win

1. **A live, honest accuracy number (the centerpiece).** Take 10 real rounds from the last ~90 days. Hide each round, keeping only data dated before it. Run Raise and check whether the actual lead investor lands in the top 20. Show it next to a **baseline** (simply ranking the most active investors overall). For example: "Raise: 6/10 in top-20. Naive baseline: 2/10." Report whatever the real number is. Honesty with a baseline beats a cherry-picked claim. No team at earlier editions had a measured evaluation.
2. **Run it on Crustdata itself, live on stage.** "Here's who Raise says Crustdata should pitch next." The CEO sees his own company.
3. **Conflict check with receipts.** "Excluded: led [competitor]'s Seed in March 2026 [source]."
4. **Warm-intro paths.** "Your co-founder overlapped 2 years at Flipkart with this partner [source]." This uses person enrich work-history overlap.
5. **Every claim cited, with "unavailable" when there's no source.** The citation validator drops unsupported claims, and the UI shows "2 unsupported claims removed." Rules decide the ranking and the LLM only explains it, a pattern several strong ContextCon 03 projects used.

**Watcher:** the free `POST /watch/company/search/{id}/test` sends a sample alert on demand, so the Slack ping fires live during the demo.

---

## 3. What we cut (from the API audit)
- **Social post search:** off by default (403). Use web search for investor news instead.
- **Founder work-history verification:** a paid add-on at 10 credits per person. It's not central to Raise, so treat it as an optional "investor-ready profile check" only if `/account/endpoints` shows it enabled.
- **Job search:** redundant, since enrich already returns `hiring.recent_openings`.
- **Agent Search beta:** a nice-to-have, and may return 403. Direct company search is the main path.

---

## 4. Tonight's checklist (no project code if rules forbid prep code)
- [ ] Crustdata account and API key. Call `GET /account/endpoints?status=disabled` (free) and note what's disabled. (You may only get the hackathon key tomorrow. In that case this is the first thing at 9:00.)
- [ ] Anthropic API key with credit, a Slack workspace with an Incoming Webhook, and cloudflared/ngrok installed.
- [ ] Python 3.12 + uv, Node 20 + pnpm, Claude Code and Antigravity logged in.
- [ ] Crustdata tooling for your agents: MCP `https://install.crustdata.com/mcp`. Claude plugin: `claude plugin marketplace add crustdata/skills` then `claude plugin install crustdata@crustdata-plugin`.
- [ ] Read: company search reference, company enrich (funding.milestones, people, competitors), person search/enrich, watcher discovery and the test endpoint, rate limits, pricing.
- [ ] Put SPEC.md (see `claude/SPEC.md`) into the empty repo plan.
- [ ] Pick **12 candidate eval companies** that raised Seed or Series A in roughly the last 90 days with a known lead (use public news). You'll keep the 10 whose Crustdata data has the lead investor.
- [ ] Pick 3 demo startups: Crustdata, one Indian startup, and one the judges might know.
- [ ] Rehearse the pitch out loud twice, then **sleep 7 hours**.

---

## 5. Hour-by-hour (solo + 3 coding agents)
| Time | Work | Checkpoint |
|---|---|---|
| 9:00–9:45 | Get keys, check `/account/endpoints`, make one real call per endpoint and save it to `fixtures/`. **Check that `lead_investors` is populated for the eval companies.** Write `models.py`/`types.ts` by hand and freeze them. | Go/no-go on Raise (see fallback) |
| 9:45–12:00 | Agent A: Crustdata client + cache + rate limits. Agent B: peer discovery + investor aggregation + ranking. Agent C: UI against fixture SSE. | CLI: domain → ranked investors |
| 12:00–1:00 | Conflict check, citation validator, outreach drafts | **1 PM cut-line:** if behind, drop warm intros and the watcher |
| 1:00–3:00 | Warm-intro paths (partner person search + overlap), wire SSE to the UI | |
| 3:00–4:30 | **Eval harness:** 10 held-out rounds plus baseline, results table | **4:30 feature freeze** |
| 4:30–5:30 | Watcher + `/test` → Slack. Record demo runs with `MODE=record`. | |
| 5:30–6:30 | Backup video (2.5 min). Rehearse in replay mode. | |
| 6:30–9:00 | Bug fixes only, 4–5 rehearsals, Q&A drill | |

Show your build to the Crustdata engineers around 2 PM. You'll get feedback, and they'll know your project before judging.

---

## 6. Pitch (3:00)
- **0:00–0:20 Hook:** FutureAdvisor replaced the financial advisor. Raise replaces the fundraising advisor who takes 2–8%.
- **0:20–0:45 Problem:** founders spend months pitching the wrong investors, ones who don't lead at their stage or who already backed a competitor. The fix today is an expensive advisor or a spreadsheet.
- **0:45–1:55 Live demo:** run on Crustdata (or a startup the judges suggest). Trace streams → ranked investors with "led 3 Seed rounds in your space [sources]" → a conflict excluded → a partner with a warm-intro path → an approved, cited outreach email → the Slack alert fires.
- **1:55–2:25 Proof:** the eval table on 10 held-out real rounds versus the baseline.
- **2:25–2:50 How + business:** Crustdata company search → enrich (funding milestones, competitors, founders) → person search/enrich → watcher. Rules rank and the LLM explains. Pricing: a flat monthly fee during a raise, a fraction of an advisor's success fee. *Use an estimate and label it as one.*
- **2:50–3:00 Close:** "Raise doesn't give you a list. It gives you your next term sheet's shortlist, with receipts."

**Q&A cheat sheet:**
- *"Isn't this just a database lookup?"* → The value is the reasoning chain: peers → who led → stage/recency/geo fit → conflicts → the right partner → intro path → cited outreach. Plus a measured eval.
- *"How accurate?"* → Show the eval with its baseline, and its limits honestly (10 rounds, Crustdata coverage).
- *"Leakage in your eval?"* → Rounds dated on or after the held-out round are filtered out deterministically before ranking. Show that code.
- *"Who pays?"* → Founders mid-raise; accelerators and incubators (a seat for their whole cohort); later, investors buying "who's raising in my space".
- *"What did you build today?"* → Be exact and honest.

---

## 7. Fallback (decided by 9:45 AM)
If `lead_investors`/`investors` turn out to be sparse for Seed/Series A companies, switch to **Scout**: pre-raise founder scouting, matching Crustdata's flagship top-5-VC case study. It watches for stealth formation, senior engineers leaving hot companies and first key hires, then produces a live watcher alert → cited one-pager → drafted outreach held for approval. It reuses the same client, cache, citation validator, UI and watcher. None of the ContextCon 03 teams ran watchers live, which is the differentiator.

---

## 8. Unverified (check at 9 AM)
Enum values for `funding.last_round_type` (seed/pre_seed); the exact shape of `people.founders`; the Slack notification object shape for watchers; how far back headcount and funding history goes; whether verification, social posts and Agent Search are enabled on the hackathon key; ContextCon 05 judging criteria (never published for any edition).
