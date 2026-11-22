# ContextCon 05: Sourced — build & pitch plan

**Event:** Sun Nov 22, 9 AM–9 PM, BITS Pilani. Sponsor: Crustdata (YC F24). Theme:
"Services, Replaced." Format: a working live demo is mandatory, ~3-minute demo + 2
minutes Q&A at finals (per the Builder Handbook's finals section: 2 min demo + 1 min
questions at the stage itself — budget the shorter number, over-rehearse the shorter
cut).

---

## 1. What we're building, one paragraph

**Sourced** takes a hiring brief, finds candidates on Crustdata's person graph, and — the
part that makes it a service rather than a search box — verifies every CV/profile claim
line by line against the live record before it ever recommends someone. A claim that
checks out is cited. A claim that contradicts the record gets the candidate flagged or
rejected, with the contradiction shown. A claim nothing settles is marked "can't
verify" instead of guessed. Two people sharing a name are shown as an unresolved
disambiguation, never silently merged into one. The shortlist that survives this gets a
cited outreach draft, held for a human to approve before it goes anywhere — and nothing
sends twice, even if the process is killed mid-run.

## 2. Why this beats a plain sourcing tool, and why it beats Raise

| Concern | Answer |
|---|---|
| "Every hackathon has a recruiting bot." | Sourcing is the commodity part. The product is the verification engine — refusing to recommend a candidate whose story doesn't survive a claim-by-claim check is not something Clay/Apollo/a typical sourcing tool does, and it's the single heaviest-weighted pair of criteria in the finals rubric: Facts and verification (20) + Robustness and edge cases (20) = 45 of 100 points map almost directly onto this one mechanic. |
| "Who pays for this today?" | Two real, already-existing fee markets, not an invented buyer: recruiting placement fees (commonly 8–25% of first-year CTC in India) **and** background-check fees (per-candidate, paid by the hiring company, the business SpringVerify/AuthBridge-style firms already run). *These percentages are estimates — cite a real source for the figure used on stage, don't present them as verified facts without one, per the rulebook's own "source for every claim" rule.* |
| vs. Raise (Investing track) | Raise's buyer is a flip (sells to founders instead of the funds who actually pay scouts today) and uses 7 of 8 Crustdata endpoints by choice. Sourced's buyer is the literal existing payer, and every one of the 8 endpoints is load-bearing, not optional — see the cheatsheet's closing note. |
| Hard-case story | The handbook hands Hiring its hard cases directly: "the right engineer calls the job something else, changed roles last month, shares a name with two strangers." Those are exactly disambiguation, employer-claim verification, and the "can't verify" branch — we don't have to invent edge cases, we have to handle the ones already specified. |

## 3. What we cut going in
- No real outbound email/LinkedIn send, no real calendar write — the handbook's own
  rule ("keep your agents in the room") makes this a non-choice, not a shortcut. Sandbox
  webhook stands in for both, which also makes idempotency trivial to demo honestly.
- No founder-work-history-verification add-on beyond what `person/enrich` already gives
  for free — nothing paid beyond the core four enrich/search/identify calls plus
  web-search for gap-filling.
- `job/search` is calibration context, not a sourcing path — don't over-build this into
  a second sourcing pipeline.

## 4. Tonight's checklist
- [ ] Crustdata account + API key; `GET /account/endpoints?status=disabled` and note
      what's off.
- [ ] Anthropic API key with credit, a Slack workspace + Incoming Webhook (the
      sandbox), cloudflared/ngrok installed.
- [ ] Python 3.12 + uv, Node 20 + pnpm, Claude Code logged in.
- [ ] Crustdata MCP: `https://install.crustdata.com/mcp`.
- [ ] Read: person search + autocomplete, person enrich (`experience.employment_details`),
      company identify, company enrich (`headcount` series specifically), job search,
      web search + fetch, watcher (company-search shape — confirm person-shape at 9 AM),
      rate limits, pricing.
- [ ] Put `SPEC.md` into the empty repo plan.
- [ ] Gather ~12 candidate eval-Set-A cases: real, documented hires from the last
      ~90 days with a sourced-before-the-hire job posting; keep the ones whose hire has
      a resolvable Crustdata profile.
- [ ] Write 10–15 eval-Set-B fixtures (synthetic, clearly fictional names) by hand
      tonight: one duplicate-name case, one contradicted-claim case, one unconfirmable
      case, one implausible-seniority case, at least one clean true-positive. This is
      the centerpiece and the cheapest thing to have ready early.
- [ ] Pick 1 demo brief to rehearse on (a role at a company judges will recognize, e.g.
      "Backend Engineer, Crustdata" — same "run it on the sponsor" move Raise used).
- [ ] Rehearse the pitch twice. Sleep 7 hours.

## 5. Hour-by-hour (solo + 3 coding agents)
| Time | Work | Checkpoint |
|---|---|---|
| 9:00–9:45 | Keys, `/account/endpoints`, one real call per endpoint saved to `fixtures/raw/`. Confirm `person/enrich` returns usable `experience.employment_details` for a test profile. Write and freeze `models.py`/`types.ts`. | Go/no-go on Sourced (see §6 fallback) |
| 9:45–12:00 | Agent A: client + cache + rate limits + ledger. Agent B: brief parsing + sourcing + disambiguation + enrichment. Agent C: UI against fixture SSE. | CLI: brief → sourced, disambiguated candidate list |
| 12:00–1:00 | Verification engine (claim extraction + matcher), company-context sanity check | **1 PM cut-line:** if behind, drop market calibration (`job/search`) and defer watcher |
| 1:00–3:00 | Ranking, outreach/rejection drafting + citation validator, approval endpoints, idempotent sandbox send | |
| 3:00–4:30 | **Both eval sets**: Set A hit-rate + baseline, Set B verification accuracy table | **4:30 feature freeze** |
| 4:30–5:30 | Watcher + `/test` → sandbox. Record demo runs with `MODE=record`. | |
| 5:30–6:30 | Backup video (2.5 min). Rehearse in replay mode, including a deliberate kill-and-restart. | |
| 6:30–9:00 | Bug fixes only, 4–5 rehearsals, Q&A drill | |

Show the build to the Crustdata engineers around 2 PM — same move Raise made, and it
gets eyes on the project before judging starts.

## 6. Fallback (decide by 9:45 AM)
If `person/enrich` turns out too thin to verify claims meaningfully for the candidates
we can actually source (small profiles, missing dates), narrow scope to **Career Check
only**: skip live sourcing, accept a CV/profile link directly from the demo "client,"
and sell the verification engine alone as a background-check replacement. Same models,
same verification engine, same two eval sets (Set A becomes "did we correctly validate
a documented real hire's actual CV" instead of a shortlist hit-rate) — it's a subset of
the same build, not a different one.

## 7. Pitch (3:00, cut to 2:00 if the stage format is the Builder Handbook's finals slot)
- **0:00–0:20 Hook:** Recruiting firms get paid when someone starts; background-check
  firms get paid per candidate. Sourced does both jobs in one pass, with the paper
  trail either job currently just... trusts.
- **0:20–0:45 Problem:** A shortlist is easy. Knowing which three lines of each CV are
  actually true, before a bad hire costs three months, is the expensive part today —
  and it's usually skipped or outsourced separately.
- **0:45–1:55 Live demo:** run the brief → trace streams through sourcing →
  disambiguation catches a name collision live → verification flags one contradicted
  claim with the record shown side-by-side → shortlist renders with
  verification-confidence chips → approve one outreach, approve one rejection → kill
  the process → restart → show nothing double-sent, the run picks up where it left off.
- **1:55–2:25 Proof:** both eval headline numbers — shortlist hit-rate vs. baseline,
  verification accuracy on the planted-error set.
- **2:25–2:50 How + business:** the full endpoint chain from the cheatsheet; cite a
  real source for the placement-fee/background-check-fee figures used, live, not a
  memorized number.
- **2:50–3:00 Close:** "A shortlist is a guess. A verified shortlist is a hire you can
  defend."

**Q&A cheat sheet**
- *"Isn't this just a database lookup?"* → The value is refusing to recommend what the
  record doesn't support — the verdict logic, the disambiguation, the sanity-check
  against company size at the claimed date, and a measured verification-accuracy eval.
- *"How accurate?"* → Show both eval numbers and their limits honestly (profile
  coverage, number of cases).
- *"What if Crustdata's data is wrong or stale?"* → Every verdict carries the record's
  retrieval date; a stale record is still cited as of that date, and a claim it can't
  settle is marked unconfirmed, not assumed false.
- *"Who pays?"* → Hiring companies, on the existing placement-fee or
  background-check-fee model — cite the real figure on stage.
- *"What did you build today?"* → Be exact and honest, same as Raise's own cheat sheet
  says.
