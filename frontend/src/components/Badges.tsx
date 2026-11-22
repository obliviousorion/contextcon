import type { Label } from "../types";
import { STATUS_META, type DisplayStatus } from "../lib/status";

export function StatusBadge({ status }: { status: DisplayStatus }) {
  const m = STATUS_META[status];
  return <span className={`chip ${m.tint} ${m.text}`}>{m.label}</span>;
}

const LABEL_HINT: Record<Label, string> = {
  "profile-derived count": "A count derived from public profiles; a lower bound, not a payroll figure.",
  estimate: "An estimated range, not a reported figure.",
  "true at retrieval only": "Describes the record when the copy was retrieved, not any earlier date.",
  "as recorded": "Exactly what the record states.",
};

/** The label is part of the fact: always visible, with its meaning available to hover and screen readers. */
export function LabelBadge({ label }: { label: Label }) {
  return (
    <span className="tag" title={LABEL_HINT[label]}>
      {label}
      <span className="sr-only">: {LABEL_HINT[label]}</span>
    </span>
  );
}

export function KindBadge({ kind }: { kind: "clearance" | "dispute" }) {
  return <span className="tag uppercase tracking-wide">{kind === "clearance" ? "Clearance file" : "Dispute file"}</span>;
}
