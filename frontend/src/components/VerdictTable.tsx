import type { AuditReport, ClaimVerdict } from "../types";
import { fieldLabel, REFUSAL_WORDS } from "../lib/format";
import { EvidenceChips } from "./EvidenceChips";

const VERDICT: Record<ClaimVerdict["verdict"], { label: string; cls: string }> = {
  agree: { label: "Agrees", cls: "bg-ok-tint text-ok" },
  contradict: { label: "Contradicts", cls: "bg-stale-tint text-stale" },
  cannot_verify: { label: "Cannot verify", cls: "bg-refuse-tint text-refuse" },
};

export function VerdictTable({ report, claimText }: { report: AuditReport; claimText?: Record<string, string> }) {
  return (
    <section className="surface" aria-labelledby="verdicts-head">
      <div className="border-b border-line p-5">
        <p className="eyebrow">Audit report <span className="font-mono normal-case">{report.id}</span></p>
        <h2 id="verdicts-head" className="text-xl">
          {report.entity?.name ?? "Unresolved company"}: {report.verdicts.length} {report.verdicts.length === 1 ? "claim" : "claims"}
        </h2>
        <p className="mt-1 text-meta text-muted">
          Each verdict cites the record line it rests on. Growth or ratio claims are never derived from two counts.
        </p>
      </div>
      <ol className="divide-y divide-line">
        {report.verdicts.map((v) => {
          const m = VERDICT[v.verdict];
          return (
            <li key={v.claim_id} className="p-5">
              <div className="flex flex-wrap items-center gap-2.5">
                <span className="font-mono text-sm text-muted">{v.claim_id}</span>
                <span className={`chip ${m.cls}`}>{m.label}</span>
                <span className="tag">{fieldLabel(v.line.field)}</span>
                {v.line.point_date && <span className="font-mono text-sm">point {v.line.point_date}</span>}
              </div>
              {claimText?.[v.claim_id] && (
                <p className="mt-2 text-ink">Claim: “{claimText[v.claim_id]}”</p>
              )}
              <p className="mt-2 text-ink"><span className="font-semibold">Statement: </span>{v.line.statement}</p>
              {v.line.refusal_code && (
                <p className="mt-1 text-sm text-refuse">
                  {REFUSAL_WORDS[v.line.refusal_code]} <span className="font-mono text-meta">({v.line.refusal_code})</span>
                </p>
              )}
              {v.line.missing && (
                <p className="mt-1 text-ink"><span className="font-semibold">What would settle it: </span>{v.line.missing}</p>
              )}
              <details className="mt-2">
                <summary className="cursor-pointer text-sm text-accent">Full reason</summary>
                <p className="mt-1 text-sm text-muted">{v.reason}</p>
              </details>
              <div className="mt-2">
                {/* The audit response carries evidence ids but no evidence map, so these are labels only. */}
                <EvidenceChips ids={v.line.evidence_ids} evidence={{}} onOpen={() => undefined} />
              </div>
            </li>
          );
        })}
      </ol>
    </section>
  );
}
