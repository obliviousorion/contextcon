# AsOf architecture

Modules: `backend/engine/` (pure rules), `backend/pipeline/` (resolve, case files, CLI wiring), `backend/platform/` (MCP server, outbox, run state, watchers), `backend/crust/` (Crustdata client).

```mermaid
flowchart TD
  subgraph Front["Front doors"]
    MCP["MCP server (stdio)<br/>backend/platform/mcp_server.py<br/>tools: resolve, attest, clear_counterparty, dispute_file,<br/>observe, audit_claims, request_evidence, watch, issue, cost<br/>NO approve tool"]
    CLI["CLI: python -m backend.cli<br/>same functions + approve, show, watch_test"]
  end
  Human(["Person<br/>CLI approve only"])
  API["Pipeline api.py<br/>resolver, case-file assembly"]
  ENG["Engine (pure, no network)<br/>attest / observe / audit rules<br/>thresholds from config.yaml"]
  RS["Run state<br/>atomic temp file + rename<br/>resume = 0 new calls, torn files detected"]
  LIM["Limits: 40 credits, 300 s<br/>over limit gives BUDGET_HELD"]

  subgraph Crust["Crust client (backend/crust)"]
    CACHE["Cache<br/>live / record / replay"]
    RATE["Rate limiter"]
    RETRY["RETRY: 429 and 5xx backoff,<br/>timeout backoff then SOURCE_UNAVAILABLE<br/>402 hard stop, 403 endpoint disabled"]
    LEDGER[("LEDGER<br/>every call: credits and INR<br/>cost shown in every CaseFile")]
  end
  CD[["Crustdata API<br/>autocomplete, identify, enrich, web/enrich/live, watchers"]]

  subgraph Out["Outbox and approvals"]
    APPR{{"APPROVAL GATE<br/>issue_case_file, issue_audit_report,<br/>send_evidence_request, create_watcher, exceed_budget"}}
    OUTBOX["actions.execute: pending persisted BEFORE effect,<br/>then done, then effects.jsonl line (fsync)<br/>reconcile on restart, never blind re-send"]
    EFF[("effects.jsonl")]
  end
  subgraph Sbx["Sandbox"]
    WH["SANDBOX_WEBHOOK_URL (https)<br/>or sandbox_outbox.jsonl<br/>receiver dedupes on idempotency_key"]
  end
  WAT["Watchers<br/>create (held), /test free, poll runs<br/>dedupe key sha(watch_id, company_id, field, signal_date)<br/>alert: re-attest today, snapshot, mark lines STALE"]

  MCP --> API
  CLI --> API
  API --> ENG
  API --> RS
  API --> LIM
  API --> CACHE
  CACHE --> RATE --> RETRY --> CD
  RETRY --> LEDGER
  CACHE -. "cache hit: 0 credits" .-> LEDGER
  LEDGER -. "cost" .-> API
  API -->|"draft"| APPR
  Human -->|"approve"| APPR
  APPR --> OUTBOX
  OUTBOX --> EFF
  OUTBOX --> WH
  API --> WAT
  WAT -->|"create_watcher held"| APPR
  WAT --> CACHE
  WAT -->|"STALE marks"| API
```

## Where the three controls sit
- **Retries:** inside the crust client (429 and 5xx wait and retry; timeouts back off, then the source is marked `SOURCE_UNAVAILABLE`; 402 stops the run). `backend/platform/util.py::with_retry` does the same for platform calls. Retries never touch the outbox: an irreversible action is not retried by the retry loop, it is reconciled by key.
- **Approvals:** one gate between a drafted item and the outbox. Approval transitions state once (a double click is a no-op). `execute_approved` refuses anything not approved. Only the CLI can approve.
- **Ledger:** at the bottom of the crust client, so every network call and every cache hit is recorded in credits and INR. The pipeline reads it to fill `CaseFile.cost`. In replay, spent is 0 and the recorded cost of the stored copies is shown separately.

## Why these pieces
- The engine has no network, so a rule is testable with a fixture and cannot spend credits.
- The outbox writes intent before effect, so a kill leaves a pending record to reconcile rather than a lost or doubled send.
- Known window: a kill after the send function returns but before the effects line is appended can repeat the send on restart. The webhook receiver must dedupe on `idempotency_key`.
