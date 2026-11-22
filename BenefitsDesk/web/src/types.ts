// Copied verbatim from web/CONTRACT.md (only `export` added so modules can import them).
/* eslint-disable @typescript-eslint/no-explicit-any */
export type Source = { record: string;          // e.g. "crustdata /person/enrich" or "crustdata /job/search"
  record_id?: string; field_path?: string; passage?: string; url?: string;
  record_date?: string | null; retrieved_at: string };
export type Fact = { fact_id: string; statement: string; value: any;
  label: "told" | "checked" | "guessed"; source: Source | null;
  conflict?: { told: any; checked: any } };
export type Belief = { belief_key: string; statement: string; value: number | null; n: number;
  version: number; valid_from: string; valid_to: string | null; suppressed: boolean;
  reason?: string; sources: Source[] };
export type Gap = { rule_id: string; cover: string; held: string; called_for: string;
  severity: "high" | "medium" | "low"; explanation: string; facts_used: string[] };
export type Figure = { metric: string; value?: string | number; period?: string; source?: Source;
  cannot_verify?: boolean; missing?: string };
export type Insurer = { insurer: string; rank: number | null; figures: Figure[]; reasons: string[] };
export type Action = { key: string; run_id: string; action: "submit_application" | "conversion_request";
  summary: string; status: "awaiting_approval" | "approved" | "sending" | "done" | "failed";
  reversible: boolean; cost_note: string; approved_by?: string; approved_at?: string;
  done_at?: string; payload: any };
export type CaseFile = {
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

// ---- Endpoint shapes from the endpoint table (not in the types block) ----
export type PreparedRequest = { file: string; id: string; type: string; said: string };
export type RunSummary = { run_id: string; request_id: string; type: string; status: string; started: string; finished: string | null };
export type EventStatus = "start" | "done" | "skipped" | "held" | "failed" | "killed" | "finished";
export type RunEvent = { id: string | number; ts: string; run_id: string; step: string; status: EventStatus; msg: string };
export type LedgerRow = { ts: string; step: string; endpoint: string; credits: number; inr: number; cache_hit: boolean; status: string };
export type Ledger = { rows: LedgerRow[]; total: { credits: number; inr: number; calls: number; cache_hits: number }; cap: number };
export type SandboxReceipt = { key: string; received_at: string; action: string; count: number };
