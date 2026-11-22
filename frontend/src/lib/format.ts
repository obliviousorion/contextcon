import type { CostSummary, JsonValue, RefusalCode } from "../types";

const DATE_FMT = new Intl.DateTimeFormat("en-IN", { day: "2-digit", month: "short", year: "numeric", timeZone: "UTC" });
const DATETIME_FMT = new Intl.DateTimeFormat("en-IN", {
  day: "2-digit", month: "short", year: "numeric", hour: "2-digit", minute: "2-digit", hour12: false,
  timeZone: "Asia/Kolkata", timeZoneName: "short",
});
const INR_FMT = new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR", minimumFractionDigits: 2, maximumFractionDigits: 2 });
const NUM_FMT = new Intl.NumberFormat("en-IN");
const USD_COMPACT = new Intl.NumberFormat("en-US", { notation: "compact", maximumFractionDigits: 1 });

/** "2026-11-22" -> "22 Nov 2026". Date-only strings are read as calendar dates (no timezone shift). */
export function fmtDate(iso: string | null | undefined): string {
  if (!iso) return "undated";
  const d = new Date(iso.length === 10 ? `${iso}T00:00:00Z` : iso);
  return Number.isNaN(d.getTime()) ? iso : DATE_FMT.format(d);
}

/** ISO datetime -> "22 Nov 2026, 16:43 IST". */
export function fmtDateTime(iso: string | null | undefined): string {
  if (!iso) return "unknown";
  const d = new Date(iso);
  return Number.isNaN(d.getTime()) ? iso : DATETIME_FMT.format(d);
}

export function fmtInr(n: number): string {
  return INR_FMT.format(n);
}

/** Python's `:g` for the small credit numbers the backend prints (2.2, 0, 6.6). */
export function fmtCredits(n: number): string {
  return `${Number(n.toPrecision(6))} ${n === 1 ? "credit" : "credits"}`;
}

/** Same wording as backend/pipeline/api.py cost_note(). */
export function costNote(c: CostSummary): string {
  const mode = c.calls === 0 && c.cache_hits > 0 ? "replay" : "live";
  return `₹${c.inr.toFixed(2)} spent this run (${mode}); ₹${c.recorded_inr.toFixed(2)} measured cost of the stored copies (${Number(c.recorded_credits.toPrecision(6))} credits)`;
}

function isRecord(v: JsonValue): v is { [key: string]: JsonValue } {
  return typeof v === "object" && v !== null && !Array.isArray(v);
}

/** Human-readable value. Revenue bands keep both bounds; nothing is rounded into a different claim. */
/** Fields whose numbers are years or ids, never quantities: no thousands separator. */
const PLAIN_NUMBER_FIELDS = new Set(["existence"]);

export function fmtValue(v: JsonValue | null | undefined, field?: string): string {
  if (v === null || v === undefined) return "—";
  if (typeof v === "number") return field && PLAIN_NUMBER_FIELDS.has(field) ? String(v) : NUM_FMT.format(v);
  if (typeof v === "string") return v;
  if (typeof v === "boolean") return v ? "yes" : "no";
  if (Array.isArray(v)) return v.map((x) => fmtValue(x)).join(", ");
  if (isRecord(v) && typeof v.lower_bound_usd === "number" && typeof v.upper_bound_usd === "number") {
    return `USD ${USD_COMPACT.format(v.lower_bound_usd)} to ${USD_COMPACT.format(v.upper_bound_usd)}`;
  }
  return JSON.stringify(v);
}

export const FIELD_LABEL: Record<string, string> = {
  existence: "Existence",
  listing: "Listing",
  headcount: "Headcount",
  revenue_band: "Revenue band",
  domains: "Domains",
};

export function fieldLabel(f: string): string {
  return FIELD_LABEL[f] ?? f.replace(/_/g, " ");
}

export const REFUSAL_WORDS: Record<RefusalCode, string> = {
  CANNOT_RESOLVE: "The input does not point to exactly one company",
  CANNOT_ATTEST: "The record does not contain this field",
  NOT_YET_RECORDED: "No data point on or before this date",
  STALE_DATA: "The nearest data point is too old to attest",
  BEFORE_FOUNDING: "The date is before the recorded founding year",
  FUTURE_DATE: "The date is after the stored copy was retrieved",
  NO_RECORD_TYPE: "Not a record type AsOf attests",
  SOURCE_UNAVAILABLE: "The source did not answer; silence is not an answer",
  BUDGET_HELD: "The run hit its credit or time limit; it can resume",
};

export function looksLikeDomain(s: string): boolean {
  const t = s.trim();
  return t.includes(".") && !/\s/.test(t);
}

/** Strip scheme, path and "www." so "https://www.delhivery.com/x" -> "delhivery.com". */
export function normalizeDomainInput(s: string): string {
  return s.trim().replace(/^[a-z]+:\/\//i, "").replace(/\/.*$/, "").replace(/^www\./i, "").toLowerCase();
}

export const ISO_DATE = /^\d{4}-\d{2}-\d{2}$/;
