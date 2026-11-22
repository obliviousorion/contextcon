import type { AttestLine, Evidence } from "../types";
import { fieldLabel, fmtValue, REFUSAL_WORDS } from "../lib/format";
import { displayStatus, STATUS_META } from "../lib/status";
import { LabelBadge, StatusBadge } from "./Badges";
import { EvidenceChips } from "./EvidenceChips";

interface Props {
  line: AttestLine;
  evidence: Record<string, Evidence>;
  onOpenEvidence: (e: Evidence) => void;
  quiet?: boolean;
}

/** Grid shared by lines and gutter markers: [point date][status rule][content]. */
export const GUTTER_GRID = "grid grid-cols-[5.75rem_3px_minmax(0,1fr)] gap-x-3 sm:grid-cols-[7rem_3px_minmax(0,1fr)] sm:gap-x-5";

/** One attestation line in the date gutter layout. */
export function LineRow({ line, evidence, onOpenEvidence, quiet = false }: Props) {
  const status = displayStatus(line);
  const meta = STATUS_META[status];
  const refused = line.status === "cannot_attest";

  return (
    <li className={`${GUTTER_GRID} py-4 pr-5 sm:pr-6`}>
      <div className="pt-0.5 text-right">
        <span className="sr-only">Point date </span>
        <time dateTime={line.point_date ?? undefined} className={`font-mono text-meta sm:text-sm ${line.point_date ? "text-ink" : "text-muted"}`}>
          {line.point_date ?? "undated"}
        </time>
        {line.gap_days != null && (
          <div className="font-mono text-meta text-refuse">{line.gap_days} d before D</div>
        )}
      </div>
      <div className={`${meta.rule} rounded-sm`} aria-hidden="true" />
      <div className="min-w-0">
        <div className="flex flex-wrap items-center gap-x-2.5 gap-y-1.5">
          <h3 className={`font-sans text-[15px] font-semibold ${quiet ? "text-muted" : "text-ink"}`}>{fieldLabel(line.field)}</h3>
          <StatusBadge status={status} />
          {line.label && <LabelBadge label={line.label} />}
        </div>

        {line.value != null && (
          <p className={`mt-1.5 break-words font-mono ${quiet ? "text-[15px] text-later" : "text-lg text-ink"}`}>
            {fmtValue(line.value, line.field)}
          </p>
        )}

        <p className={`mt-1.5 break-words ${quiet ? "text-muted" : "text-ink"}`}>{line.statement}</p>

        {line.stale && (
          <p className="mt-2 rounded border-l-2 border-stale bg-stale-tint px-3 py-1.5 text-sm text-stale">
            {line.stale_note ?? "STALE: a watcher alert reports newer data; re-attest before relying on this line."}
          </p>
        )}

        {refused && (
          <div className="mt-2.5 rounded border border-line bg-refuse-tint px-3 py-2">
            {line.refusal_code && (
              <p className="text-sm text-refuse">
                <span className="font-medium">{REFUSAL_WORDS[line.refusal_code]}</span>{" "}
                <span className="font-mono text-meta">({line.refusal_code})</span>
              </p>
            )}
            {line.missing && (
              <p className="mt-1 text-ink">
                <span className="font-semibold">What would settle it: </span>
                {line.missing}
              </p>
            )}
          </div>
        )}

        <div className="mt-2.5">
          <EvidenceChips ids={line.evidence_ids} evidence={evidence} onOpen={onOpenEvidence} />
        </div>
      </div>
    </li>
  );
}

/** A marker row in the gutter, e.g. the as-of date D or the "Dated after D" divider. */
export function GutterMarker({ date, title, note }: { date: string; title: string; note?: string }) {
  return (
    <li className={`${GUTTER_GRID} items-center bg-sunken py-2.5`} aria-label={`${title}: ${date}`}>
      <div className="text-right">
        <span className="font-mono text-meta font-medium text-accent sm:text-sm">{date}</span>
      </div>
      <div className="flex h-full items-center justify-center" aria-hidden="true">
        <span className="h-2 w-2 rounded-full bg-accent" />
      </div>
      <div className="min-w-0">
        <span className="text-sm font-semibold text-accent">{title}</span>
        {note && <span className="ml-2 text-meta text-muted">{note}</span>}
      </div>
    </li>
  );
}
