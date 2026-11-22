import type { AttestLine } from "../types";

export type DisplayStatus = "attested" | "cannot_attest" | "subsequent_event" | "stale";

/** Text + color pairs. The text is always rendered; color is never the only signal. */
export const STATUS_META: Record<DisplayStatus, { label: string; text: string; tint: string; rule: string }> = {
  attested: { label: "Attested", text: "text-ok", tint: "bg-ok-tint", rule: "bg-ok" },
  cannot_attest: { label: "Cannot attest", text: "text-refuse", tint: "bg-refuse-tint", rule: "bg-refuse" },
  subsequent_event: { label: "Subsequent event", text: "text-later", tint: "bg-later-tint", rule: "bg-later" },
  stale: { label: "Stale", text: "text-stale", tint: "bg-stale-tint", rule: "bg-stale" },
};

export function displayStatus(line: AttestLine): DisplayStatus {
  return line.stale ? "stale" : line.status;
}
