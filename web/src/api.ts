import type { Action, Belief, CaseFile, Ledger, PreparedRequest, RunSummary, SandboxReceipt } from "./types";

export class BackendDownError extends Error {
  constructor() {
    super("Backend not running");
    this.name = "BackendDownError";
  }
}

type Listener = (down: boolean) => void;
const listeners = new Set<Listener>();
let lastDown = false;
function setDown(down: boolean) {
  if (down !== lastDown) {
    lastDown = down;
    listeners.forEach((l) => l(down));
  }
}
export function onBackendStatus(l: Listener) {
  listeners.add(l);
  l(lastDown);
  return () => {
    listeners.delete(l);
  };
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let res: Response;
  try {
    res = await fetch(path, {
      ...init,
      headers: { Accept: "application/json", ...(init?.body ? { "Content-Type": "application/json" } : {}), ...(init?.headers || {}) },
    });
  } catch {
    setDown(true);
    throw new BackendDownError();
  }
  const text = await res.text();
  let data: unknown = undefined;
  try {
    data = text ? JSON.parse(text) : undefined;
  } catch {
    // Vite's dev proxy answers 500/502/504 with a non-JSON body when the backend is down.
    if (res.status >= 500 || res.status === 404) {
      setDown(true);
      throw new BackendDownError();
    }
    throw new Error(`Unexpected response from ${path}`);
  }
  if (data === undefined && (res.status >= 500 || res.status === 404)) {
    setDown(true);
    throw new BackendDownError();
  }
  setDown(false);
  if (!res.ok) {
    const errField = data && typeof data === "object" && "error" in data ? (data as { error: unknown }).error : undefined;
    throw new Error(errField ? String(errField) : `${res.status} ${res.statusText}`);
  }
  return data as T;
}

const post = <T,>(path: string, body: unknown) => request<T>(path, { method: "POST", body: JSON.stringify(body) });

export const api = {
  requests: () => request<PreparedRequest[]>("/api/requests"),
  run: (file: string) => post<{ run_id: string }>("/api/run", { file }),
  kill: (run_id: string) => post<{ killed: boolean }>("/api/kill", { run_id }),
  resume: (run_id: string) => post<{ run_id: string }>("/api/resume", { run_id }),
  runs: () => request<RunSummary[]>("/api/runs"),
  caseFile: (run_id: string) => request<CaseFile | { status: "running" }>(`/api/runs/${encodeURIComponent(run_id)}`),
  ledger: (run_id: string) => request<Ledger>(`/api/ledger?run_id=${encodeURIComponent(run_id)}`),
  approvals: () => request<Action[]>("/api/approvals"),
  approve: (key: string) => post<{ approved: boolean; already: boolean }>("/api/approve", { key, approver: "person" }),
  act: (run_id: string) => post<unknown>("/api/act", { run_id }),
  sandbox: () => request<SandboxReceipt[]>("/api/sandbox"),
  correctFact: (persona_id: string, fact_id: string, value: unknown) => post<unknown>("/api/facts", { persona_id, fact_id, value }),
  beliefs: (group: string) => request<Belief[]>(`/api/beliefs?group=${encodeURIComponent(group)}`),
};

export function isCaseFile(x: CaseFile | { status: "running" } | null | undefined): x is CaseFile {
  return !!x && x.status !== "running" && "run_id" in x;
}
