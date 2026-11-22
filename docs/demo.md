# Demo: 2 minutes

All commands ran in replay on 2026-11-22. Replay makes no network calls and spends 0 credits.

## Setup (before the clock starts)
```bash
cd contextcon
uv sync
export MODE=replay ASOF_TODAY=2026-11-22 ASOF_STATE_DIR="$(mktemp -d)"
asof() { uv run python -m backend.cli "$@"; }
```
Do not set `MODE=record` or `MODE=live`.

## UI path (same beats, in the browser)
The CLI beats below are the reference. The same beats run in the web UI, against the real backend:
```bash
uv run python -m backend.http_api            # terminal 1: API on 127.0.0.1:8787; note the approval token it prints
cd frontend && npm install && npm run dev    # terminal 2: UI on http://127.0.0.1:5173
```
| Beat | In the browser |
|---|---|
| 1 | Home → "Shree Balaji Logistics" chip → "Cannot resolve: 25 companies match", each with a Check button; nothing is picked. |
| 1b | Home → `drl.aero` chip → two companies share the domain. |
| 2 | Check `delhivery.com` → five lines in the date gutter, each with its label. Click E4 → the drawer shows the endpoint, field path and the quoted excerpt. The header reads "₹0.00 spent this run (replay); ₹62.12 measured cost of the stored copies (2.2 credits)". |
| 3 | Dispute file → presets `2020-01-01` (418, attested) then `2026-10-15` (Cannot attest, "38 d before D", "What would settle it"). The URL changes, so Back works. |
| 4 | Issue case file → "Held for approval" and the token dialog → paste the token from terminal 1 → Approved by, at → Issued (sandbox), sent exactly once. Click again: nothing new is sent. Show the kill with the CLI chaos run below. |
| 5 | Watch → request a watcher for `delhivery.com` → approve with the token → issue → fire the test alert → the headcount line is marked STALE, with a link to the file. |
| Close | Ledger → spent this run vs measured cost per file. |

Live variant (spends credits only after a click): start terminal 1 with `--live --cap 10`. A company that is not stored shows "Live lookup needed: about 2.2 credits (₹62.12)"; only "Spend about 2.2 credits and fetch" calls Crustdata, and the response is cached so it is never paid for twice.

## Beat 1 (0:00-0:25): the raw Crustdata MCP guesses, AsOf refuses
1. In Claude, with Crustdata's own MCP added (`claude mcp add --transport http crustdata https://install.crustdata.com/mcp`), ask about "Shree Balaji Logistics". Use a real recorded run of that answer; it is not produced by this repo (TODO(lead): capture it).
2. Then AsOf:
```bash
asof resolve "Shree Balaji Logistics"
```
Real output (the `candidates` list has 25 entries; trimmed here):
```
status: cannot_resolve   entity: null   candidates: 25   missing: "a domain"
```

## Beat 1b (0:25-0:40): the hardest case, drl.aero
```bash
asof resolve drl.aero
```
Real output:
```json
{ "status": "cannot_resolve", "entity": null,
  "candidates": [
    {"crustdata_company_id": 5798,     "name": "Delhivery",          "domains": ["drl.aero","delhivery.com"], "confidence": 1.0},
    {"crustdata_company_id": 15944579, "name": "Delhivery Robotics", "domains": ["drl.aero"],                 "confidence": 1.0}
  ],
  "missing": "a domain that matches exactly one company" }
```
Say: Delhivery's record lists drl.aero, so we first assumed they were one company. A 0.2-credit live check found two. An alias is a claim, not proof.

## Beat 2 (0:40-1:05): a clearance file with its cost
```bash
asof clear delhivery.com
```
Five lines, each cited (real values from the replay):
```
existence     attested  2011            Data point dated 2026-11-22 states year_founded 2011; stored copy retrieved 2026-11-22T11:13:09+00:00.
listing       attested  listed          Data point dated 2022-05-24 states IPO date 2022-05-24 (symbols: DELHIVERY); ...
headcount     attested  35295           (profile-derived count) Data point dated 2026-11-16 states employee_count 35295; ...
revenue_band  attested  1e9 to 1e12 USD (estimate) Data point dated 2026-11-18 ...
domains       attested  drl.aero, delhivery.com   (true at retrieval only)
cost: {"credits": 0.0, "inr": 0.0, "calls": 0, "cache_hits": 2, "recorded_credits": 2.2, "recorded_inr": 62.12}
cost_note: "Rs 0.00 spent this run (replay); Rs 62.12 measured cost of the stored copies (2.2 credits)"
```
(The output uses the rupee sign.) The file id looks like `CF-38e15ccbbde1` and is stable for the same request. Save it: `CF=<id>`.

Note: the existence line carries the retrieval date as its point date, because the record states only a founding year. That is as recorded; it is not a claim about 2011 events.

## Beat 3 (1:05-1:25): move the date
```bash
asof attest tciexpress.in headcount 2020-01-01
asof attest tciexpress.in headcount 2026-10-15
```
Real output (fields `line.status`, `line.value`, `line.point_date`, `line.refusal_code`, `line.gap_days`):
```
attested 418 2019-12-30
  "Data point dated 2019-12-30 states employee_count 418; stored copy retrieved 2026-11-22T11:13:15+00:00."
cannot_attest  STALE_DATA  gap_days 38
  "a headcount.timeseries point within 14 days before 2026-10-15; the nearest point on or before 2026-10-15 is dated 2026-09-07, 38 days earlier"
```
Optional dispute file and side by side:
```bash
asof dispute delhivery.com 2022-06-01     # existence, listing attested; headcount and revenue_band NOT_YET_RECORDED
asof observe tciexpress.in headcount 2020-01-01 2026-09-01   # 418 and 1715, no growth verdict
```

## Beat 4 (1:25-1:45): approve, kill mid-send, restart, sent once
Approval is a person's act, from the CLI (there is no MCP approve tool):
```bash
asof approve $CF        # {"status":"approved","first_approval":true,"approved_by":"<you>", ...}
asof issue $CF          # {"action":"issue_case_file","status":"done","key":"38e15c..."}
asof issue $CF          # same output again; no second effect
wc -l "$ASOF_STATE_DIR/effects.jsonl"     # 1
```
Now the kill. The chaos harness SIGKILLs a slow sender at random moments 5 times, restarts it, and checks that no action ran twice:
```bash
export ASOF_STATE_DIR="$(mktemp -d)"
uv run python tests/chaos_kill.py --cmd "uv run python tests/platform/demo_actions.py" \
  --effects "$ASOF_STATE_DIR/effects.jsonl" --rounds 5 --expect-keys 3 --seed 7 --max-delay 0.8
```
Real output:
```
seed=7
round 1: killed@0.29s
round 2: killed@0.16s
round 3: killed@0.54s
round 4: killed@0.10s
round 5: killed@0.45s
final run exit=0 in 0.8s
effects=3 distinct=3 torn_lines=0
CHAOS: PASS
```
`sandbox_outbox.jsonl` ends with 3 lines. Say the caveat: a kill between the send returning and the effects line can repeat one send, so the receiver dedupes on `idempotency_key`.

Note: `demo_actions.py` is the harness's three-action sender, not the `issue` command itself. The kill demonstrates the outbox; `issue` is shown twice above to show a repeat is a no-op.

## Beat 5 (1:45-2:00): watcher `/test` marks a line STALE
A watcher needs a case file to mark. Use a fresh state dir:
```bash
export ASOF_STATE_DIR="$(mktemp -d)"
asof clear delhivery.com > /dev/null
asof watch delhivery.com            # held_for_approval; prints watch_id_handle "watch:<hex>"
W=watch:<hex>
asof approve $W
asof issue $W                       # status created, watch_id w-<hex>
asof watch_test $W                  # status alert, stale_line_ids ["CF-...#headcount"], alert_cost_credits 5.0
asof watch_test $W                  # status no_op: duplicate signal date
```
Real output of the first test: `alert ['CF-38e15ccbbde1#headcount']`, and the second returns `{"status": "no_op", "reason": "duplicate signal date (or monthly alert cap)"}`. A real alert costs 5 credits (Rs 141.18); `/test` is free.

## Close
`asof cost` (in a state dir where `clear` already ran, e.g. Beat 2's) shows the ledger: 0 spent this run, 2.2 credits (Rs 62.12) measured per clearance file. The Rs 600 price is an estimate.

## Backup path (no live commands, no kill)
1. Run the suite: `uv run pytest -q` (212 passed, 0 xfail, about 7 seconds).
2. Show the recorded ledger: `cat fixtures/live_check/ledger/phase4-record-2026-11-22.jsonl` (7.8 credits across the live record run).
3. Show the stored answers: `tests/cases/hidden_test_cases.json` (C08 25 candidates, C17 two candidates).
4. Show the chaos result: `CHAOS: PASS`, exactly one send per key across 5 random kills.
5. The chaos harness output above is deterministic with `--seed 7`.
