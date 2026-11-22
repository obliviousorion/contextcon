# Idea rules — give this file to your agent

These rules keep every idea comparable, sourced and reviewed the same way. If you are an AI agent: read this whole file before doing anything in `ideas/`, follow it exactly, and say which section you are following when you report back.

## 0. Before you start
1. `git pull` and read, in this order:
   - [../README.md](../README.md), the leaderboard;
   - [_council/PROCESS.md](_council/PROCESS.md);
   - the current champion [01-asof.md](01-asof.md);
   - the rules in `ContextCon05_BITS_Problem_Statement.pdf` (repo root; `pdftotext -layout <file> -`).
2. Read [_council/round2-brief-and-data-check.md](_council/round2-brief-and-data-check.md) for the real Crustdata data limits. Never contradict those facts without new live evidence.
3. Check the leaderboard for an existing idea that already covers yours. If one does, improve that idea's document (see §4) instead of adding a duplicate.

## 1. Hard constraints every idea must satisfy
An idea that fails any of these is marked **Dropped** with the reason.
- It serves the one fictional Indian 3PL client from the problem statement.
- It does a whole paid service job, from the request to the result.
- Every fact in its output links to the exact passage or field it came from, plus that record's date. No facts from model memory.
- When sources can't settle a question, it answers **"cannot verify"** and names what is missing. A wrong answer counts against us more than "cannot verify".
- Irreversible actions (sending anything outside, payments, rejections, suspensions) wait for a human.
- Each run has a cost limit and a time limit, and the cost of every call is recorded in a ledger.
- It survives a kill and restart with each action happening exactly once.
- It never contacts real outside people. A "send" means our own sandbox webhook.
- It is unique. The event judges said track-example builds are overdone: hiring screeners, vendor checks, investor scouts, invoice matchers and the like. Say explicitly why other teams won't build yours.

## 2. Evidence rules (non-negotiable)
- **Rupee figures:** every fee or price is either sourced (link to a rate card, quote, filing or statute) or labelled `(estimate)`. Never present an estimate as fact.
- **Cost per job:** compute it from the known Crustdata prices:

  | Call | Credits |
  |---|---|
  | company identify, per match (unmatched is free) | 0.2 |
  | company enrich, per record | 2 |
  | person enrich | 1 |
  | person or company search, per result | 0.03 |
  | web search | 1 |
  | watch alert | 5 |
  | watch create, run reads, `/test`, autocomplete, account endpoints | 0 |

  Convert at ≈ ₹26 per credit ($0.30 × ₹88). Mark any price you had to guess, for example web fetch, which hasn't been measured yet.
- **Data claims:** any claim about what Crustdata returns must cite a recorded response, or be labelled `UNVERIFIED`. Known traps:
  - headcount is a profile-derived count, so don't claim what it includes or excludes;
  - weekly series have gaps of up to ~5 months;
  - never compute growth from two lower-bound counts;
  - resolving by name alone is unsafe (one name returned 25 candidates).
- **No inventing endpoints.** 23 endpoints are disabled on our key (all `/batch/*`, contact enrich, employee reviews, social posts, the live professional-network searches); see the data-check file. Use only enabled ones.

## 3. Live API calls and credits
- **Default: no live calls.** Use the recorded responses we already have.
- When an idea genuinely needs a data check:
  - ask the team in chat first, stating the exact calls and estimated credits; keep it **≤ 10 credits** per check;
  - run it through the project's Crustdata client in `MODE=record`, so every response is cached for free replay;
  - commit the recorded responses under `fixtures/` and log the credits spent in the idea's document.
- Never print, paste or commit `.env` or any API key.

## 4. Adding or editing an idea
- **New idea:** copy [_TEMPLATE.md](_TEMPLATE.md) to `ideas/NN-short-slug.md`, using the next free number. Fill **every** section; if something is unknown, write `UNKNOWN` and why.
- **Editing someone else's idea:** don't rewrite their sections. Append under `## Discussion` with your name, the date and what you propose. The idea's owner merges it.
- **Merging ideas:** create one document that lists its parents. Mark the parents `Merged into NN` and keep their documents; never delete history.
- The champion document is edited only after a council round, or by team agreement.

## 5. Review process: how an idea gets on the leaderboard
1. **Round 1 — five-lens review.**
   - Run the five judge prompts in [_council/JUDGE_PROMPTS.md](_council/JUDGE_PROMPTS.md) (CS, Ethics, Finance, Builder, Novelty), each in a separate agent session, read-only.
   - Each scores 1–5 using the anchors in that file. Save each output verbatim to `_council/reviews/NN-<lens>-<YYYYMMDD-HHMM>.md`.
   - The Round 1 score is the sum (max 25). Never score your own idea in the same session that wrote it.
2. **Round 2 — head-to-head.**
   - An idea scoring **≥ 19**, or beating the lowest current finalist, plays head-to-head against the current top 3.
   - Run the three head-to-head prompts (CS and robustness, Ethics and finance, Novelty and buildability). Each plays every pairwise matchup and names a winner with a one-line reason.
   - Save the outputs to `_council/reviews/`.
3. **Fact-check:** at least one judge checks the idea's data claims against recorded fixtures and lists any that are contradicted or unverified.
4. **Leaderboard update:** update the table in `../README.md` with the new scores, wins, status and link.
   - Reorder by Round 2 wins first, then Round 1 score.
   - If the top 3 changes, rewrite the top-3 detail sections from the idea documents.
   - State in the commit message which reviews justify the change.

## 6. Git workflow
- Pushing straight to `main` or opening a pull request are both fine. Use whichever is easier.
- `git pull` before you start and again before you push, so you don't overwrite someone else's leaderboard update.
- Keep one idea or one review round per commit where you can. The commit message says what changed and how many credits were spent, if any.
- Never commit `.env`, keys, or the local build repo (`sourced*/` is gitignored).
- If you're an AI agent, end your commits with your own co-author line.

## 7. What a good report back looks like (for agents)
1. Which sections of these rules you followed.
2. The files you created or changed.
3. The scores or verdicts you produced, plus any data claim you couldn't verify.
4. The credits spent: 0 unless the team approved a data check.
5. Open questions for the team.
