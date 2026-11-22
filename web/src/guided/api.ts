// Types and calls for the guided flow. Shapes follow web/GUIDED_CONTRACT.md exactly.
/* eslint-disable @typescript-eslint/no-explicit-any */

export type Source = { record: string; record_id?: string; field_path?: string; passage?: string; url?: string;
  record_date?: string | null; retrieved_at?: string };
export type Label = "told" | "checked" | "guessed";
export type Stage = "confirm" | "questions" | "dashboard" | "refused";
export type Mode = "live" | "replay";

export type IntakeItem = { key: "employer" | "role" | "start_date" | "city" | "age_band"; label: string; value: any;
  kind: "checked" | "guessed" | "missing"; source?: Source | null; basis?: string; question?: string; choices?: string[] };
export type Fact = { fact_id: string; statement: string; value: any; label: Label;
  source: Source | null; cannot_verify?: boolean; missing?: string; last_checked?: string };
export type TrailStep = { key: "you" | "employer" | "people" | "insurers" | "gaps"; title: string; searched: string; source: string;
  records: number | null; credits: number; status: "found" | "searched, cannot verify" | "skipped" | "computed" | "running";
  mode: "live" | "replay" | "no call"; recorded_at?: string | null; reused?: boolean; note?: string; pointers: Source[] };
export type InsurerFact = { label: string; value: any; source: Source };
export type Insurer = { company_id: number; name: string; facts: InsurerFact[];
  claims: { cannot_verify: true; missing: string } | { value: string; source: Source }[] };
export type DiaryEntry = { date: string; subject: string; subject_kind: "you" | "group"; new: string; previous: string | null;
  trigger: string; source: Source | null; label: Label; gap_changed: boolean; next_step_changed: boolean };
export type Gap = { rule_id: string; cover: string; called_for: string; severity: string; explanation: string; facts_used: string[] };
export type Dashboard = {
  user: { user_id: string; mode: Mode; stage: string; last_checked: string | null };
  as_of: string;
  dates: string[];
  run: { run_id: string | null; status: "running" | "finished" | "held" | "stopped" | "none" };
  profile: Fact[];
  graph_case: { facts: Fact[]; peer_benchmark: any | null };
  insurers: { note: string; selection: any; items: Insurer[]; status: string; missing?: string };
  gaps: Gap[];
  questions: { question: string; why: string }[];
  cannot_verify: { statement: string; missing: string }[];
  trail: TrailStep[];
  next_step: { choices: { company_id: number; name: string }[]; action: any | null; conversion: any | null };
  diary: DiaryEntry[];
  cost: { credits: number; inr: number };
};
export type Me = { logged_in: boolean; user_id?: string; stage?: Stage; mode?: Mode };

export class ApiError extends Error {
  constructor(message: string, public status: number) { super(message); }
}

export async function api<T>(url: string, body?: unknown): Promise<T> {
  let r: Response;
  try {
    r = await fetch(url, body === undefined
      ? { credentials: "same-origin" }
      : { method: "POST", credentials: "same-origin", headers: { "content-type": "application/json" }, body: JSON.stringify(body) });
  } catch {
    throw new ApiError("Could not reach the server. Check your connection and try again.", 0);
  }
  let data: any = null;
  try { data = await r.json(); } catch { /* empty or non-JSON body */ }
  if (!r.ok) throw new ApiError((data && typeof data.error === "string") ? data.error : `The server answered ${r.status}.`, r.status);
  return data as T;
}

export const errText = (e: unknown) => (e instanceof Error ? e.message : String(e));
