// Types matching backend/models.py (FROZEN contracts) plus the HTTP envelopes in backend/http_api.py.
// Dates are ISO strings: `date` -> "YYYY-MM-DD", `datetime` -> ISO 8601 with offset.

export type FieldName = "existence" | "listing" | "headcount" | "revenue_band" | "domains";
export const FIELD_NAMES: FieldName[] = ["existence", "listing", "headcount", "revenue_band", "domains"];

export type LineStatus = "attested" | "cannot_attest" | "subsequent_event";

export type RefusalCode =
  | "CANNOT_RESOLVE"
  | "CANNOT_ATTEST"
  | "NOT_YET_RECORDED"
  | "STALE_DATA"
  | "BEFORE_FOUNDING"
  | "FUTURE_DATE"
  | "NO_RECORD_TYPE"
  | "SOURCE_UNAVAILABLE"
  | "BUDGET_HELD";

export type Label = "profile-derived count" | "estimate" | "true at retrieval only" | "as recorded";

/** JSON value as the backend sends it (AttestLine.value is `Any`). */
export type JsonValue = string | number | boolean | null | JsonValue[] | { [key: string]: JsonValue };

export interface Evidence {
  id: string;
  kind: "company_record" | "web_page" | "watch_alert";
  source_endpoint: string;
  url: string | null;
  field_path: string | null;
  excerpt: string;
  point_date: string | null;
  retrieved_at: string;
  cache_key: string | null;
}

export interface Candidate {
  crustdata_company_id: number;
  name: string | null;
  domains: string[];
  confidence: number | null;
}

export interface Entity {
  crustdata_company_id: number;
  name: string | null;
  domains: string[];
  resolved_by: "domain" | "id";
  evidence_id: string | null;
}

export interface ResolveResult {
  status: "resolved" | "cannot_resolve";
  entity: Entity | null;
  candidates: Candidate[];
  missing: string | null;
}

export interface AttestLine {
  field: string;
  as_of: string;
  status: LineStatus;
  value: JsonValue | null;
  point_date: string | null;
  label: Label | null;
  statement: string;
  refusal_code: RefusalCode | null;
  missing: string | null;
  gap_days: number | null;
  evidence_ids: string[];
  /** Added only by GET /api/files/{id} when a watcher alert marked the line. */
  stale?: boolean;
  stale_note?: string;
}

export interface CostSummary {
  credits: number;
  inr: number;
  calls: number;
  cache_hits: number;
  recorded_credits: number;
  recorded_inr: number;
}

export interface Attestation {
  entity: Entity;
  as_of: string;
  lines: AttestLine[];
  subsequent_events: AttestLine[];
  generated_at: string;
}

export type DraftStatus = "draft" | "approved" | "issued_sandbox";

export interface EvidenceRequest {
  target: string;
  items: string[];
  note: string;
  status: "draft" | "approved" | "sent_sandbox";
  idempotency_key: string;
}

export interface CaseFile {
  id: string;
  kind: "clearance" | "dispute";
  request: { tool?: string; domain?: string; as_of?: string; [key: string]: JsonValue | undefined };
  resolve: ResolveResult;
  attestation: Attestation | null;
  evidence: Record<string, Evidence>;
  evidence_request: EvidenceRequest | null;
  cost: CostSummary;
  status: DraftStatus;
  idempotency_key: string;
}

export interface ClaimInput {
  id: string;
  text: string;
  field: string;
  value: JsonValue | null;
  as_of: string | null;
}

export interface ClaimVerdict {
  claim_id: string;
  verdict: "agree" | "contradict" | "cannot_verify";
  line: AttestLine;
  reason: string;
}

export interface AuditReport {
  id: string;
  entity: Entity | null;
  verdicts: ClaimVerdict[];
  status: DraftStatus;
  idempotency_key: string;
}

export interface WatchSnapshot {
  watch_id: string;
  crustdata_company_id: number;
  field: string;
  signal_date: string;
  snapshot_hash: string;
  dedupe_key: string;
  stale_line_ids: string[];
}

// ---- HTTP envelopes (backend/http_api.py) ------------------------------------------------------

export interface Health {
  ok: boolean;
  mode: string;
  today: string;
  /** usd_per_credit x inr_per_usd from config.yaml */
  inr_per_credit: number;
  watch_alert_credits: number;
  live_enabled: boolean;
  session_cap_credits: number;
  session_spent_credits: number;
  session_left_credits: number;
}

/** Live server, request not in the stored copies: nothing was spent; re-send with confirm to fetch. */
export interface SpendGate {
  needs_confirmation: true;
  reason: string;
  estimate_credits: number;
  estimate_inr: number;
  basis: string;
  live_enabled: boolean;
  session_cap_credits: number;
  session_spent_credits: number;
  session_left_credits: number;
}

export function isSpendGate(x: unknown): x is SpendGate {
  return typeof x === "object" && x !== null && (x as { needs_confirmation?: unknown }).needs_confirmation === true;
}

export type CasefileResponse = { caseFile: CaseFile; cost_note?: string } | { resolve: ResolveResult } | SpendGate;

export interface AttestResponse {
  line: AttestLine;
  subsequent_events: AttestLine[];
  evidence: Record<string, Evidence>;
}

export interface ObserveResponse {
  lines: [AttestLine, AttestLine];
}

export interface CostFileRow {
  id: string;
  kind: "clearance" | "dispute";
  domain: string | null;
  credits: number;
  inr: number;
  recorded_credits: number;
  recorded_inr: number;
  label: string;
}

export interface CostResponse {
  case_files: CostFileRow[];
  ledger_credits_spent: number;
  ledger_inr_spent: number;
  total_recorded_credits: number;
}

export interface ApprovalRecord {
  by: string;
  at: string;
}

export interface StaleMark {
  line: string;
  field: string;
  snapshot: WatchSnapshot;
  newer_point: string | null;
}

export type StoredArtifact = CaseFile | AuditReport | EvidenceRequest;

export interface FileDetail {
  artifact: StoredArtifact;
  approval: ApprovalRecord | null;
  stale: StaleMark[];
}

export interface IssueResponse {
  id: string;
  action?: string;
  status: "held_for_approval" | "done" | "failed" | "pending" | "created";
  note?: string;
  key?: string;
  watch_id?: string | null;
}

export interface ApproveResponse {
  id: string;
  status: "approved" | "held_for_approval";
  first_approval?: boolean;
  approved_by?: string;
  approved_at?: string;
  note?: string;
}

export type WatchResponse =
  | {
      /** "created" when this domain's watcher was already approved and created earlier. */
      status: "held_for_approval" | "created";
      key: string;
      domain: string;
      company_id: number;
      field: string;
      watch_id: string | null;
      next: string;
    }
  | { status: "cannot_resolve"; missing: string | null };

export type WatchTestResponse =
  | {
      status: "alert";
      snapshot: WatchSnapshot;
      stale_line_ids: string[];
      current_line: AttestLine;
      alert_cost_credits: number;
    }
  | { status: "no_op"; reason: string; snapshot: WatchSnapshot; current_line: AttestLine };

export function isCaseFile(a: StoredArtifact): a is CaseFile {
  return "kind" in a && "attestation" in a;
}
export function isAuditReport(a: StoredArtifact): a is AuditReport {
  return "verdicts" in a;
}
