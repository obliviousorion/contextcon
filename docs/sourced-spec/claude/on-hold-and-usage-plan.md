# On-hold and usage plan — Sourced

What happens when a limit is hit, in order of how often each one will actually fire
during the event.

## Credit budget per run
Estimated cost for a 10-candidate brief, verification included:
| Step | Endpoint | Calls | Est. credits |
|---|---|---|---|
| Source | `person/search` | 1 | ~1.2 (40 results × 0.03) |
| Verify | `person/enrich` | 10 | ~20 (2cr × 10, batched ≤25) |
| Resolve employers | `company/identify` | ~25 (2–3 employers × 10 candidates) | ~5 (0.2cr × matched only) |
| Sanity-check seniority | `company/enrich` | ~10 (one per flagged seniority claim) | ~20 |
| Market calibration | `job/search` | 1 | ~1 |
| Gap-filling | `web/search` + `web/fetch` | ~6 (budgeted, load-bearing claims only) | ~6 |
| **Total** | | | **~55–60cr**, budget cap set to **150cr** per run to leave headroom for retries and a second brief |

Model-token cost (brief parsing, claim extraction, verdict narration, outreach/rejection
drafting) is tracked in the same `LedgerEntry` list, in tokens, not converted to
credits — the UI shows both numbers side by side rather than a single blended figure,
since blending them would hide which one is actually the bottleneck on a given run.

## Hitting the cap mid-run
The run does not truncate the candidate list silently and does not guess the rest.
It transitions to a `held_for_approval`-shaped state (`TraceEvent.status = "error"`,
message = "budget cap reached at candidate 7/10") with everything computed so far
intact and resumable — a person can approve spending more, or accept the partial
shortlist. This mirrors Rule 4 from the project rulebook (a ceiling on every run, with a
visible ledger) and Rule 5 (a timeout or a stop is "unknown," never silently treated as
"done" or "failed").

## Rate limits — token buckets
| Endpoint | Limit | Where it bites |
|---|---|---|
| `person/search` | 30/min | Only hit once per run unless the brief is re-run |
| `person/enrich` | 15/min | Batch ≤25 profile URLs per call; a 10-candidate run is 1 call |
| `company/enrich` | 15/min | Up to ~10 calls per run (one per flagged seniority claim) — space these, don't fire all at once |
| `company/search` | 30/min | One per run (target-company set) |
| `job/search` | 30/min | One per run |
| `web/search/live` | **10/min — the real constraint** | Budget: only claims that are both unconfirmed and load-bearing get a web-search call; a 10-candidate run should need ≤6 |
| `watch/*` | 10/min | 3–5 watcher creations per demo, well under the limit |

Retry policy on 429/5xx: backoff 1s, 2s, 4s, then surface as a `TraceEvent` error for
that one candidate/claim — never block the whole run on one failed call.

## Cache modes
- `live`: read-through cache, writes new entries.
- `record`: same as live, but flags every entry for inclusion in the demo fixture set.
- `replay`: cache-only; a miss is an error event, never a silent network fallback —
  this is what makes the demo's kill-and-restart honest (nothing new is fetched mid-demo
  that wasn't already proven to work live).

Cache key: `sha256(path + canonical request body)`. Non-2xx responses are never cached.

## Demo mode
`DEMO=1` replays `fixtures/runs/{id}.jsonl` over SSE at 0.3× the original call delays,
so the live trace still reads as "live" without waiting on real network latency. Hidden
toggle: press "d". The kill-and-restart portion of the demo should still run against
the real idempotency logic (not a scripted fake "restart"), since that's the one claim
in the pitch that a judge might actually test by asking to see it again.

## What "approval" blocks, concretely
Three action types are gated, matching the rulebook's "a person approves anything you
can't undo":
1. **Outreach send** (to the sandbox, standing in for a real candidate).
2. **Rejection notice send** (explicitly called out in the handbook's "what every
   service does" table — rejecting an applicant is not a free action).
3. **Call booking** (a slot going from `proposed` to `booked`).

Nothing else in the pipeline waits on a human — sourcing, verification, ranking, and
drafting all run unattended, because none of them are irreversible.
