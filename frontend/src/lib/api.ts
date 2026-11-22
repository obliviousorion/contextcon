import type {
  ApproveResponse,
  AttestResponse,
  AuditReport,
  CasefileResponse,
  ClaimInput,
  CostResponse,
  EvidenceRequest,
  FileDetail,
  Health,
  IssueResponse,
  ObserveResponse,
  SpendGate,
  WatchResponse,
  WatchTestResponse,
} from "../types";

/** Relative by default (Vite proxies /api to the API server). VITE_API_URL overrides it. */
const BASE: string = (import.meta.env.VITE_API_URL as string | undefined)?.replace(/\/$/, "") ?? "";

export class ApiError extends Error {
  constructor(
    message: string,
    readonly status: number,
    /** true when the server could not be reached at all */
    readonly network = false,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

type Query = Record<string, string | undefined>;

function qs(params: Query): string {
  const sp = new URLSearchParams();
  for (const [k, v] of Object.entries(params)) if (v !== undefined && v !== "") sp.set(k, v);
  const s = sp.toString();
  return s ? `?${s}` : "";
}

async function request<T>(method: "GET" | "POST", path: string, body?: unknown, headers?: Record<string, string>,
  signal?: AbortSignal): Promise<T> {
  let res: Response;
  try {
    res = await fetch(`${BASE}${path}`, {
      method,
      signal,
      headers: body === undefined ? headers : { "content-type": "application/json", ...headers },
      body: body === undefined ? undefined : JSON.stringify(body),
    });
  } catch (e) {
    if (e instanceof DOMException && e.name === "AbortError") throw e;
    throw new ApiError("Cannot reach the AsOf API server.", 0, true);
  }
  const text = await res.text();
  let data: unknown = null;
  try {
    data = text ? JSON.parse(text) : null;
  } catch {
    // A non-JSON reply usually means the dev proxy could not reach the API (it answers 500/502 itself).
    throw new ApiError(res.ok ? "The server sent a reply that is not JSON." : "Cannot reach the AsOf API server.",
      res.status, !res.ok);
  }
  if (!res.ok) {
    const msg = data && typeof data === "object" && "error" in data && typeof data.error === "string"
      ? data.error : `${res.status} ${res.statusText}`;
    throw new ApiError(msg, res.status);
  }
  return data as T;
}

const get = <T>(path: string, signal?: AbortSignal) => request<T>("GET", path, undefined, undefined, signal);
const post = <T>(path: string, body: unknown, headers?: Record<string, string>) =>
  request<T>("POST", path, body, headers);

export const api = {
  health: (signal?: AbortSignal) => get<Health>("/api/health", signal),
  casefile: (tool: "clear" | "dispute" | "resolve", domain: string, asOf?: string, signal?: AbortSignal,
    confirm = false) =>
    get<CasefileResponse>(`/api/casefile${qs({ tool, domain, as_of: asOf, confirm: confirm ? "1" : undefined })}`,
      signal),
  attest: (domain: string, field: string, asOf: string, signal?: AbortSignal) =>
    get<AttestResponse>(`/api/attest${qs({ domain, field, as_of: asOf })}`, signal),
  observe: (domain: string, field: string, d1: string, d2: string, signal?: AbortSignal) =>
    get<ObserveResponse>(`/api/observe${qs({ domain, field, d1, d2 })}`, signal),
  file: (id: string, signal?: AbortSignal) => get<FileDetail>(`/api/files/${encodeURIComponent(id)}`, signal),
  cost: (signal?: AbortSignal) => get<CostResponse>("/api/cost", signal),
  issue: (id: string) => post<IssueResponse>("/api/issue", { id }),
  approve: (id: string, token: string) =>
    post<ApproveResponse>("/api/approve", { id }, { "X-AsOf-Approval-Token": token }),
  audit: (domain: string, claims: ClaimInput[], confirm = false) =>
    post<{ report: AuditReport } | SpendGate>("/api/audit", { domain, claims, confirm }),
  evidenceRequest: (target: string, items: string[]) =>
    post<{ request: EvidenceRequest }>("/api/evidence_request", { target, items }),
  watch: (domain: string) => post<WatchResponse>("/api/watch", { domain }),
  watchTest: (id: string) => post<WatchTestResponse>("/api/watch_test", { id }),
};

/** The store id of an evidence request (backend/pipeline/store.py: "ER-" + first 12 of its key). */
export function evidenceRequestId(er: EvidenceRequest): string {
  return `ER-${er.idempotency_key.slice(0, 12)}`;
}

export function errorMessage(e: unknown): string {
  if (e instanceof Error) return e.message;
  return String(e);
}
