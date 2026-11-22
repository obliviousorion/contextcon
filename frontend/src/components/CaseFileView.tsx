import { useState, type ReactNode } from "react";
import type { ApprovalRecord, CaseFile, Evidence, StaleMark } from "../types";
import { fmtDate } from "../lib/format";
import { CandidateList } from "./CandidateList";
import { CaseFileHeader } from "./CaseFileHeader";
import { EvidenceDrawer } from "./EvidenceDrawer";
import { EvidenceRequestCard } from "./EvidenceRequestCard";
import { GutterMarker, LineRow } from "./LineRow";
import { ApprovalStepper } from "./ApprovalStepper";

interface Props {
  cf: CaseFile;
  approval?: ApprovalRecord | null;
  stale?: StaleMark[];
  /** Rendered between the header and the lines (e.g. the dispute date control). */
  controls?: ReactNode;
}

/** The core screen: one column, one surface per section, the date gutter as the signature. */
export function CaseFileView({ cf, approval, stale = [], controls }: Props) {
  const [open, setOpen] = useState<Evidence | null>(null);
  const att = cf.attestation;
  const asOf = att?.as_of ?? cf.request.as_of ?? "";

  return (
    <div className="mx-auto max-w-file space-y-5">
      <article className="surface" aria-label={`${cf.kind} file ${cf.id}`}>
        <CaseFileHeader cf={cf} />
        {controls && <div className="border-b border-line p-5">{controls}</div>}

        {stale.length > 0 && (
          <div className="border-b border-line bg-stale-tint px-5 py-3 text-stale" role="note">
            <span className="font-semibold">STALE: </span>
            a watcher alert reported newer data for {stale.map((s) => s.field).join(", ")}
            {stale[0]?.newer_point && <> (newer point dated <span className="font-mono">{stale[0].newer_point}</span>)</>}.
            Re-attest before relying on the marked lines.
          </div>
        )}

        {att ? (
          <>
            <ol aria-label="Attestation lines" className="divide-y divide-line">
              <GutterMarker date={asOf} title="As of D" note={fmtDate(asOf)} />
              {att.lines.map((l, i) => (
                <LineRow key={`${l.field}-${i}`} line={l} evidence={cf.evidence} onOpenEvidence={setOpen} />
              ))}
            </ol>
            {att.subsequent_events.length > 0 && (
              <section aria-labelledby="subsequent-head" className="border-t border-line">
                <ol className="divide-y divide-line">
                  <li className="bg-sunken px-5 py-2.5">
                    <h2 id="subsequent-head" className="font-sans text-sm font-semibold text-later">
                      Dated after D — reported, never attested
                    </h2>
                    <p className="text-meta text-muted">
                      These points were recorded after {asOf}. They are shown for context and carry no weight in this file.
                    </p>
                  </li>
                  {att.subsequent_events.map((l, i) => (
                    <LineRow key={`sub-${l.field}-${i}`} line={l} evidence={cf.evidence} onOpenEvidence={setOpen} quiet />
                  ))}
                </ol>
              </section>
            )}
          </>
        ) : (
          <p className="p-5 text-ink">
            No lines were attested: the company could not be resolved, so nothing about it is stated.
          </p>
        )}
      </article>

      {cf.resolve.status === "cannot_resolve" && (
        <CandidateList resolve={cf.resolve} query={cf.request.domain ?? ""} />
      )}

      {cf.evidence_request && <EvidenceRequestCard key={cf.evidence_request.idempotency_key} request={cf.evidence_request} />}

      {att && <ApprovalStepper key={cf.id} id={cf.id} status={cf.status} approval={approval} noun="case file" />}

      <EvidenceDrawer evidence={open} onClose={() => setOpen(null)} />
    </div>
  );
}
