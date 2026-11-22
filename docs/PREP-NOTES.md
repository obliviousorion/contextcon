# ContextCon 05 — prep folder (NOT the hackathon repo)

> UPDATE 2026-11-22: project switched from Raise to **Sourced** (hiring desk, Career Check core). Local build repo is `sourced/` (worktrees sourced-A/B/C/D, never pushed). Raise docs archived in `docs/archive-raise/`. Real rules: `ContextCon05_BITS_Problem_Statement.pdf`. Agent prompts: `docs/prompts/`. Council: `docs/council/`.

Sunday 2026-11-22, 9:00–21:00, Pilani Campus. Crustdata (YC F24) x YC x BITS Pilani. Team of up to 4 (problem statement).
**Build lives in `contextcon/sourced/` (local git repo; branches agent-a/b/c/d as worktrees `sourced-A/B/C/D` beside it; never pushed).** Keep `.env` here in the parent (CRUSTDATA_API_KEY, CRUST_KEY, ANTHROPIC_API_KEY, SLACK_WEBHOOK_URL, PUBLIC_URL); worktrees load it via `../.env`. Final code must go in the organizer repo from kickoff.

## Files
- `docs/builder-handbook.pdf` / `.txt` — official Builder Handbook (34 pp), downloaded 2026-11-20
- `.env` — `CRUSTDATA_API_KEY` (chmod 600, gitignored). Never commit it.
- `check-key.sh` — key check: credit balance (free) + one Company Identify (~0.1 credit)

## Status (2026-11-20)
- Registered via the Google Form (Coding Club email, 2026-11-18). WhatsApp community: https://chat.whatsapp.com/EianwLt29DA3XNUU0nfcrf
- Crustdata account: BITS email, 200 trial credits (= $60, expire 2026-12-04). Key verified 2026-11-20.
- Promo code `CONTEXTCON-BITS` rejected on billing page ("isn't valid for this account") → ask Crustdata team / WhatsApp / contextcon@crustdata.co.
- Open: is a separate Y Combinator events-page registration needed? (submission checklist mentions it)

## Day schedule
9:00 check-in (college ID) · 9:45 kickoff · 10:15 API walkthrough · 10:35 team formation · **10:45 build** · 13:00 lunch ·
**14:30 checkpoint submit** · 17:30 last call · **18:00 code freeze (public repo + 2-min video)** · 18:15 CTF (solo, RE + OSINT) ·
19:30 top 10 announced · 19:45 finals (2 min demo + 1 min Q&A) · 20:40 winners.

## Scoring (100)
End-to-end execution 25 · Facts & verification 20 · Robustness & edge cases 20 · Customer value & idea 20 · Demo & understanding 15.
Ties → E2E, then facts. Finalists picked from repo + video, so the video is the entry ticket.

## Rules that matter
- Any model/framework/tool; Crustdata optional. Agents must not contact real outside people.
- Declare anything written beforehand. Commit as you go. Keep build notes (approaches tried, what worked) — judges listen for them.
- Submission: team name, one line, theme, public repo, one video link (plays in private window), how it works, public diagram link, member details (name/email as registered, roll no., personal email, GitHub username).
- Project ownership/IP: not stated anywhere — ask if it matters.

## Crustdata API
Base `https://api.crustdata.com`, headers `authorization: Bearer $KEY`, `x-api-version: 2025-11-01`.
Rate limits/min: Person Search 30, Person Enrich 15, Company Search 30, Company Identify 30 (handbook says free, but measured ~0.1 credit/call on trial 2026-11-20), Company Enrich 15, Job Search 30, Web Search+Fetch 10, Watcher 10; 200/min total per key.
Errors: 401 key · 402 out of credits (`GET /account/credits` free) · 403 endpoint not allowed · 429 back off (`x-ratelimit-reset`).
MCP: `claude mcp add --transport http crustdata https://install.crustdata.com/mcp`. Docs + llms.txt: docs.crustdata.com.
Trial pricing: search $9/1k records, autocomplete free, Person Enrich $0.30–2.10/record, Company Enrich $0.60–1.20/record — keep enrich calls for event credits.

## Plan (solo)
- Theme leaning: **5.1 Vendor Check** (name + website → real, active, run by its director? cited evidence; fronts caught, namesakes pass). Route: Company Identify → Person Enrich → Web Search.
- Prep (no code): 2–3 approaches with pros/cons on paper; 15-case test list (real firm, front, namesake, slow source); README + demo-script outline.
- Day order: one request end-to-end by ~13:00 → evidence log → robustness (retry/429, resume after crash, dedupe, "can't verify") → submit 14:30 → README + video by 17:30.
