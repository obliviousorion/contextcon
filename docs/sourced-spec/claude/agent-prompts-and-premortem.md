# Agent prompts and premortem — Sourced

## Starting each coding agent

**Agent A (Crustdata client, cache, budget, watcher)**
> You own `backend/crust/` and `backend/watch/` only. Build the Crustdata HTTP client
> (httpx async, headers from `.env`), the disk-JSON cache keyed by
> `sha256(path + canonical body)` with `live`/`record`/`replay` modes, the per-endpoint
> token-bucket rate limiter, and the credit/token ledger (`LedgerEntry`, append-only).
> Then the watcher create/list/test wrapper and a webhook receiver that forwards to the
> sandbox URL. Read `SPEC.md` §Crustdata and §Cache/credits/demo. Do not touch
> `backend/agent/` or `frontend/`. Acceptance tests are in `SPEC.md` §Acceptance tests,
> block A.

**Agent B (pipeline, verification, ranking, eval)**
> You own `backend/agent/` and `backend/eval/`. Build, in order: brief parsing →
> candidate sourcing → disambiguation → enrichment → claim extraction → verification
> (deterministic matcher first, LLM narrates second) → company-context sanity check →
> ranking → outreach/rejection drafting with the citation validator → booking
> idempotency. Then the two eval sets. Read `SPEC.md` in full — this module is most of
> the spec. Freeze `backend/models.py` once Agent A's ledger schema and your own Run
> schema agree; propose later changes in `NOTES.md`, don't just edit it. Acceptance
> tests are in `SPEC.md` §Acceptance tests, block B.

**Agent C (frontend)**
> You own `frontend/` only. Build against `fixtures/run_demo.jsonl` (a fake SSE stream)
> so you're never blocked on the backend. One page: brief input, live trace (including
> a visible "held for approval" state), ranked shortlist with a verification-confidence
> chip and disambiguation badge, a per-candidate drawer showing every claim with its
> verdict and source, approval buttons for outreach/rejection/booking, an Eval tab with
> both headline numbers, a Watch tab. Read `SPEC.md` §UI. Acceptance tests are in
> §Acceptance tests, block C.

## Prompt: brief → JobSpec
```
System: Parse a hiring brief into structured JSON:
{role_title, seniority_band, must_have_skills: [str], nice_to_have_skills: [str],
 location, remote_ok: bool, company_context: {name, domain, stage}, comp_range_hint: str|null}.
Infer nothing not stated or strongly implied. If seniority isn't stated, infer it only
from an explicit signal in the brief (years of experience, a title like "staff" or
"lead") and say which signal you used; otherwise leave it null rather than guessing.
```

## Prompt: CV/profile text → CareerClaims
See `SPEC.md` §Prompt: CV claim extraction. Key rule: extract claims as-is, including
vague ones ("led a team") — verification decides whether they hold up, extraction must
not pre-filter or soften them.

## Prompt: verdict → outreach / rejection draft
See `SPEC.md` §Prompt: outreach with citations. The rejection-notice prompt is the same
shape with one line changed: "State only the specific gap or contradiction that drove
this decision, cited. Never a generic rejection — the recruiter must be able to defend
this decision from the note alone."

## Premortem — what's likely to go wrong, and the planned response

| Risk | Likelihood | Response |
|---|---|---|
| `person/enrich` is thin or stale for the specific candidates we source (small/early-career profiles under-indexed) | Medium-high | Degrade gracefully: `verification_confidence` reflects data availability, not just match quality; "thin record, mostly unconfirmed" is a valid, shown result — never hidden or silently upgraded to "confirmed." |
| Watcher's *person*-level watch isn't actually a documented endpoint (handbook only shows a worked example for company-search watch) | Medium | Confirm the exact resource path against `docs.crustdata.com` at 9:00 AM. If person-watch doesn't exist, fall back to watching the *candidate's current employer* via `watch/company/search` for headcount/leadership changes as a weaker re-engagement signal, and say so honestly in the demo. |
| `web/search/live` at 10 RPM becomes the bottleneck once several candidates each have 1–2 unconfirmed claims | High | Budget it deliberately: only spend a web-search call on a claim that is both unconfirmed by Crustdata AND load-bearing for the ranking (a must-have skill or the seniority claim), per `SPEC.md` §6. Nice-to-have claims stay `unconfirmed` without a web-search attempt, and the UI says so rather than implying every unconfirmed claim was chased down. |
| A real name collision inside the *same* company (two "Priya Sharma"s who both worked at the claimed employer) defeats the simple disambiguation signals | Medium | This is exactly the hard case the rulebook wants surfaced, not solved perfectly — show it as an explicitly unresolved `DisambiguationGroup` with both candidates listed and the reason the signals couldn't separate them, rather than guessing. |
| Eval Set A (real historical hires) is hard to find with full Crustdata coverage by 9:45 AM | Medium | Same mitigation Raise used: gather ~12 candidate cases from public hiring announcements, keep only the ones where the actual hire has a resolvable Crustdata profile; go in with 8–10 usable cases, report however many survive. |
| Recruiter approval UI becomes a bottleneck in the 3-minute demo (too many clicks) | Low-medium | Demo script approves exactly 2 outreach drafts and 1 rejection on stage, live; the rest of the shortlist is shown but not clicked through — see the winning-plan doc's pitch timing. |
| LLM invents a seniority inference not licensed by the brief (e.g. assumes "5+ years" from a vague brief) | Medium | The brief-parsing prompt requires citing which signal licensed any inferred field; `seniority_band: null` is a valid, expected output and the ranking formula handles a null band as "no preference stated," not as a guess. |

## Unverified (check at 9 AM, same discipline as the Raise export)
Exact shape of a person-level watcher (vs. the documented company-search watcher);
whether `company/enrich`'s `headcount` series has enough history depth for pre-2024
seniority claims; whether `job/search` returns enough volume for niche titles to be a
useful market comparable rather than an empty result; ContextCon 05 judging criteria
beyond what's in the Builder Handbook (same caveat the Raise export flagged — it has
never been published in full for any edition).
