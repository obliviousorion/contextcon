// Types matching backend/models.py FROZEN contracts

export type FieldName = "existence" | "listing" | "headcount" | "revenue_band" | "domains";

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

export type Label =
  | "profile-derived count"
  | "estimate"
  | "true at retrieval only"
  | "as recorded";

export interface Evidence {
  id: string; // "E{n}"
  kind: "company_record" | "web_page" | "watch_alert";
  source_endpoint: string; // e.g. "/company/enrich"
  url?: string | null;
  field_path?: string | null; // e.g. "headcount.timeseries[2024-07-15].employee_count"
  excerpt: string; // verbatim value or passage
  point_date?: string | null;
  retrieved_at: string;
  cache_key?: string | null;
}

export interface Candidate {
  crustdata_company_id: number;
  name?: string | null;
  domains: string[];
  confidence?: number | null;
}

export interface Entity {
  crustdata_company_id: number;
  name?: string | null;
  domains: string[];
  resolved_by: "domain" | "id";
  evidence_id?: string | null;
}

export interface ResolveResult {
  status: "resolved" | "cannot_resolve";
  entity?: Entity | null;
  candidates: Candidate[];
  missing?: string | null;
}

export interface AttestLine {
  field: string;
  as_of: string;
  status: LineStatus;
  value?: any;
  point_date?: string | null;
  label?: Label | null;
  statement: string;
  refusal_code?: RefusalCode | null;
  missing?: string | null;
  gap_days?: number | null;
  evidence_ids: string[];
}

export interface CostSummary {
  credits: number;
  inr: number;
  calls: number;
  cache_hits: number;
  recorded_credits?: number;
  recorded_inr?: number;
  cost_note?: string;
}

export interface Attestation {
  entity: Entity;
  as_of: string;
  lines: AttestLine[];
  subsequent_events: AttestLine[];
  generated_at: string;
}

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
  request: Record<string, any>;
  resolve: ResolveResult;
  attestation?: Attestation | null;
  evidence: Record<string, Evidence>;
  evidence_request?: EvidenceRequest | null;
  cost: CostSummary;
  status: "draft" | "approved" | "issued_sandbox";
  idempotency_key: string;
}

export type ToolType = "clear" | "dispute" | "attest" | "resolve";

export interface FixtureOutcome {
  id: string;
  date: string;
  title: string;
  companyName: string;
  domain: string;
  tool: ToolType;
  description: string;
  caseFile?: CaseFile;
  resolveResult?: ResolveResult;
  attestLine?: AttestLine;
}
