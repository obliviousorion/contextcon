# Benefits Desk UI ↔ API contract

The backend is a Python stdlib HTTP server (`bd serve`, port 8787). It serves `web/dist/` at `/` and JSON under `/api`.
The UI must render only what the API returns: no placeholder text and no invented data. Every number and claim has a `source` you can open.

## Endpoints
| Method | Path | Body | Returns |
|---|---|---|---|
| GET | /api/requests | – | `[{file, id, type, said}]` the prepared requests in `requests/` |
| POST | /api/run | `{file}` or `{request}` | `{run_id}`; starts `bd run` as a child process |
| POST | /api/kill | `{run_id}` | `{killed: bool}`: SIGKILL to the child (the "kill" button) |
| POST | /api/resume | `{run_id}` | `{run_id}`; restarts the same run; finished steps are skipped |
| GET | /api/runs | – | `[{run_id, request_id, type, status, started, finished}]` |
| GET | /api/runs/{run_id} | – | CaseFile (below), or `{status:"running"}` while it runs |
| GET | /api/stream?run_id=X | – | **SSE**. Each `data:` is one Event `{id, ts, run_id, step, status, msg}`; status ∈ `start, done, skipped, held, failed, killed, finished` |
| GET | /api/ledger?run_id=X | – | `{rows:[{ts, step, endpoint, credits, inr, cache_hit, status}], total:{credits, inr, calls, cache_hits}, cap}` |
| GET | /api/approvals | – | `[Action]` all intents, newest first |
| POST | /api/approve | `{key, approver}` | `{approved: bool, already: bool}` (double click → `already: true`, one action) |
| POST | /api/act | `{run_id}` | executes approved actions for the run (also done by resume) |
| GET | /api/sandbox | – | `[{key, received_at, action, count}]` what the sandbox receiver got; `count` > 1 would be a duplicate |
| POST | /api/facts | `{persona_id, fact_id, value}` | the person corrects a fact; stored as a new `told` fact |
| GET | /api/beliefs?group=KEY | – | `[Belief]` every version |

## Types
```ts
type Source = { record: string;          // e.g. "crustdata /person/enrich" or "crustdata /job/search"
  record_id?: string; field_path?: string; passage?: string; url?: string;
  record_date?: string | null; retrieved_at: string };
type Fact = { fact_id: string; statement: string; value: any;
  label: "told" | "checked" | "guessed"; source: Source | null;
  conflict?: { told: any; checked: any } };
type Belief = { belief_key: string; statement: string; value: number | null; n: number;
  version: number; valid_from: string; valid_to: string | null; suppressed: boolean;
  reason?: string; sources: Source[] };
type Gap = { rule_id: string; cover: string; held: string; called_for: string;
  severity: "high" | "medium" | "low"; explanation: string; facts_used: string[] };
type Figure = { metric: string; value?: string | number; period?: string; source?: Source;
  cannot_verify?: boolean; missing?: string };
type Insurer = { insurer: string; rank: number | null; figures: Figure[]; reasons: string[] };
type Action = { key: string; run_id: string; action: "submit_application" | "conversion_request";
  summary: string; status: "awaiting_approval" | "approved" | "sending" | "done" | "failed";
  reversible: boolean; cost_note: string; approved_by?: string; approved_at?: string;
  done_at?: string; payload: any };
type CaseFile = {
  run_id: string; status: "finished" | "held" | "stopped" | "refused"; as_of: string;
  request: { id: string; type: string; said: string };
  persona?: { persona_id: string; signups: number; consent: boolean };
  facts?: Fact[];
  workplace?: { group: { key: string; employer: string; function: string; city: string };
                beliefs: Belief[]; timeline: { date: string; joiners: number; leavers: number }[] };
  peer_benchmark?: { filter: any; as_of: string; total: number;
    phrases: { phrase: string; count: number | null; share: number | null; cannot_verify?: string }[];
    any_cover: { count: number | null; share: number | null };
    by_role?: { role: string; total: number; with_cover: number }[];
    samples: { job_id: string; url: string; company: string; date_added: string; phrase: string; passage: string }[];
    note: string; source: Source };
  gaps?: Gap[];
  package?: { role: string; items: { cover: string; rule_id: string; why: string }[] }[]; // employer view
  shortlist?: Insurer[];
  alarm?: { status: "job_change" | "no_change_on_record" | "cannot_verify" | "same_company";
            old_employer?: string; new_employer?: string; change_date?: string;
            cover_end_date?: string; conversion_deadline?: string; explanation: string;
            sources: Source[] };
  actions?: Action[];
  questions?: { question: string; why: string }[];
  cannot_verify?: { statement: string; missing: string }[];
  cost: { credits: number; inr: number; calls: number; cache_hits: number; seconds: number; cap: number };
  skipped_steps?: string[];   // steps reused from the step store after a restart
};
```
