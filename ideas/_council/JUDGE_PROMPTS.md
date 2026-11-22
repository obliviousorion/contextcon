# Judge prompts (copy one per agent session; read-only reviews)

Shared preamble. Prepend it to every prompt:
> You are a judge reviewing hackathon ideas. READ-ONLY: don't edit any file except your own review file, don't call any API, don't run code unless you're checking a recorded fixture.
>
> Read first:
> - ideas/RULES.md
> - docs/builder-handbook.txt, the final source of truth, especially "How winners are picked" and "What every service does"
> - ideas/_council/round2-brief-and-data-check.md
> - the idea document(s) you are given
>
> Context (from the Handbook):
> - The scoring is: **End-to-end execution 25 · Facts and verification 20 · Robustness and edge cases 20 · Customer value and idea 20 · Demo and understanding 15**. Ties go to E2E, then Facts.
> - Facts must be right **for the day they are used**, and one company under two names stays one record.
> - "I can't verify" beats a wrong fact.
> - A person approves anything that can't be undone.
> - Each run has time and credit limits and a ledger, model calls included.
> - It survives a crash or timeout and never sends or pays twice.
> - It uses only the personal data the job needs.
> - Our own test cases must include a duplicate, a lookalike name, and a case where the answer is "I can't verify", dated after 1 Sep 2026.
> - Finals: 2 minutes of demo plus 1 minute of questions, including the scale question ("100x volume or a second client?").
> - The event judges want a non-obvious, out-of-the-box use of Crustdata. Track examples are overdone.
> - Map the lenses below onto those criteria: CS covers E2E, robustness and facts; Ethics covers the safety part of robustness; Finance covers customer value and the business case; Novelty covers customer value and the demo; Builder checks it can ship by 18:00.
>
> Save your output verbatim to `ideas/_council/reviews/NN-<lens>-<YYYYMMDD-HHMM>.md`.

## Round 1 lenses (score 1–5; each lens has anchors)

**CS (live run, robustness, design, hidden tests)**
Prompt: "Score the live run (an unseen request taken to a correct, sourced result), robustness (kill and restart, each action exactly once), design (a 5-minute live fix, '100x volume or a second client?') and fit to the hidden tests. Flag any output whose correct answer can't be written as a test."
- 5: deterministic, testable answers, and an exactly-once design with no holes.
- 3: works, but some outputs are proxies with no ground truth.
- 1: correct answers can't be tested, or it depends on unverified data.

**Ethics**
Prompt: "Score personal-data use, approvals before harmful actions, explanations, right of reply, surveillance and defamation optics, and harm from false positives."
- 5: company data only, refusal by design, every harmful step gated, explanations cited.
- 3: limited personal data, or false positives possible but gated.
- 1: profiles individuals, or implies wrongdoing, or acts on proxies.

**Finance**
Prompt: "Score the buyer, the rupee price, the measured cost per job from the price table in RULES.md §2, and whether a firm would really pay. Challenge every unsourced fee and name the source that would back it."
- 5: a named buyer who already pays, cost far below price, sources identified.
- 3: plausible, but the price is unsourced or the margin is thin.
- 1: unit economics fail, or there's no billable job.

**Builder**
Prompt: "Can a small team with coding agents ship a working, demo-able MVP that survives the hidden tests in the time left? How much existing work does it reuse (the Crustdata client with cache, replay, ledger and resume; the council harness)? What's the data risk and the demo risk? Give the cheapest live check, at most 10 credits, that would de-risk it."
- 5: reuses most assets, uses only verified data, and has safe cut-lines.
- 3: buildable, with one unverified dependency.
- 1: depends on disabled or unverified endpoints, or the scope is too large.

**Novelty and story**
Prompt: "How likely is another team to build something similar (compare against the track examples)? Would it surprise a Crustdata engineer and a YC partner? Is there a memorable 3-minute demo moment, including the kill on stage? Would it win People's Choice? Suggest a reframing that makes it feel new."
- 5: nobody else will build it, and it has a memorable live moment.
- 3: fresh angle on a common pattern.
- 1: literally a track example.

Required output for each lens, max 350 words: a table of the ideas with a 1–5 score and a reason of at most 12 words, your top 3, fatal flaws, and recommended merges.

## Round 2 head-to-head (finalists; each judge plays every pairwise matchup)
Before Round 2, each finalist gets a **champion** session that writes the strongest version of it (max 600 words): pitch, buyer and price, request types, exact calls, 4 hidden-test cases, approvals and restart, watchers, ethics, build plan with cut-lines, demo script, and the strongest attack with its rebuttal.

Judges:
1. **CS and robustness.** Also fact-checks every data claim against the recorded fixtures, and probes each restart design for holes.
2. **Ethics and finance together.** Who a wrong output harms, and the most credible buyer and price.
3. **Novelty and buildability.** Memorability, meaningful use of watchers and MCP, what ships in the time left, whether to merge, a beat-by-beat demo, and a build order.

Required output for each judge, max 450 words: every matchup with its winner and a one-line reason, a final ranking, the winner's biggest risk, and what to take from the losers into the winner.
