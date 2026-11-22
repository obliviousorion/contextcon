import React from "react";
import { AttestLine, Evidence } from "../types";
import { CheckCircle2, XCircle, AlertCircle, Calendar, Clock, Database, Tag } from "lucide-react";

interface CaseFileLineProps {
  line: AttestLine;
  evidenceMap?: Record<string, Evidence>;
  onOpenEvidence: (evidence: Evidence) => void;
  retrievedAtFallback?: string;
}

export const CaseFileLine: React.FC<CaseFileLineProps> = ({
  line,
  evidenceMap = {},
  onOpenEvidence,
  retrievedAtFallback,
}) => {
  // Find primary evidence
  const primaryEvidenceId = line.evidence_ids[0];
  const primaryEvidence = primaryEvidenceId ? evidenceMap[primaryEvidenceId] : undefined;
  const retrievedAt = primaryEvidence?.retrieved_at || retrievedAtFallback || "2026-11-22T08:03:40Z";

  // Format value display
  const renderValue = () => {
    if (line.status === "cannot_attest") {
      return <span className="text-slate-500 italic font-mono">CANNOT ATTEST</span>;
    }
    if (line.value === null || line.value === undefined) {
      return <span className="text-slate-500 font-mono">null</span>;
    }
    if (typeof line.value === "object") {
      if (line.value.lower_bound_usd && line.value.upper_bound_usd) {
        return (
          <span className="font-mono text-emerald-300">
            ${(line.value.lower_bound_usd / 1e9).toFixed(1)}B – ${(line.value.upper_bound_usd / 1e9).toFixed(1)}B USD
          </span>
        );
      }
      return <span className="font-mono text-emerald-300">{JSON.stringify(line.value)}</span>;
    }
    if (Array.isArray(line.value)) {
      return <span className="font-mono text-emerald-300">[{line.value.join(", ")}]</span>;
    }
    if (typeof line.value === "number") {
      return <span className="font-mono text-emerald-300">{line.value.toLocaleString()}</span>;
    }
    return <span className="font-mono text-emerald-300">{String(line.value)}</span>;
  };

  return (
    <div
      className={`p-4 rounded-xl border transition-all ${
        line.status === "attested"
          ? "bg-slate-900/80 border-slate-800 hover:border-slate-700"
          : line.status === "subsequent_event"
          ? "bg-purple-950/20 border-purple-900/40 hover:border-purple-800"
          : "bg-rose-950/20 border-rose-900/40 hover:border-rose-800/80"
      }`}
    >
      <div className="flex flex-col lg:flex-row lg:items-start justify-between gap-3">
        {/* Left Side: Field, Status, Value, Label */}
        <div className="space-y-2 flex-1">
          <div className="flex flex-wrap items-center gap-2">
            {/* Status Chip */}
            {line.status === "attested" && (
              <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-950 text-emerald-300 border border-emerald-800">
                <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
                attested
              </span>
            )}
            {line.status === "cannot_attest" && (
              <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-rose-950 text-rose-300 border border-rose-800">
                <XCircle className="w-3.5 h-3.5 text-rose-400" />
                cannot attest
              </span>
            )}
            {line.status === "subsequent_event" && (
              <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-purple-950 text-purple-300 border border-purple-800">
                <AlertCircle className="w-3.5 h-3.5 text-purple-400" />
                subsequent event
              </span>
            )}

            {/* Field Name */}
            <span className="text-sm font-bold text-slate-100 font-mono capitalize">
              {line.field}
            </span>

            {/* Label Chip */}
            {line.label && (
              <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[11px] font-medium bg-slate-800 text-slate-300 border border-slate-700">
                <Tag className="w-3 h-3 text-slate-400" />
                {line.label}
              </span>
            )}

            {/* Refusal Code Chip for cannot_attest */}
            {line.refusal_code && (
              <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[11px] font-mono font-semibold bg-amber-950 text-amber-300 border border-amber-800">
                {line.refusal_code}
              </span>
            )}
          </div>

          {/* Value Display */}
          <div className="text-base font-medium text-slate-200 flex items-center gap-2">
            <span className="text-xs text-slate-400">Value:</span>
            {renderValue()}
          </div>

          {/* Statement */}
          <p className="text-xs text-slate-400 leading-relaxed bg-slate-950/40 p-2.5 rounded-lg border border-slate-800/60 font-sans">
            {line.statement}
          </p>

          {/* Missing info display for refusals */}
          {line.missing && (
            <div className="text-xs bg-rose-950/30 border border-rose-900/50 p-2.5 rounded-lg text-rose-300">
              <span className="font-semibold text-rose-200">Missing: </span>
              <span>{line.missing}</span>
              {line.gap_days !== null && line.gap_days !== undefined && (
                <span className="ml-2 font-mono text-amber-300">
                  (Gap: {line.gap_days} days)
                </span>
              )}
            </div>
          )}
        </div>

        {/* Right Side: Point Date, Retrieved At, Source Chips */}
        <div className="flex flex-col sm:flex-row lg:flex-col items-start lg:items-end gap-2 text-xs text-slate-400 min-w-[240px]">
          {/* Point Date */}
          <div className="flex items-center gap-1.5 font-mono">
            <Calendar className="w-3.5 h-3.5 text-slate-500" />
            <span className="text-slate-500">Point date:</span>
            <span className="text-slate-200">{line.point_date || "n/a (undated)"}</span>
          </div>

          {/* Retrieved At */}
          <div className="flex items-center gap-1.5 font-mono">
            <Clock className="w-3.5 h-3.5 text-slate-500" />
            <span className="text-slate-500">Retrieved:</span>
            <span className="text-slate-300 text-[11px] truncate max-w-[170px]" title={retrievedAt}>
              {retrievedAt.split("T")[0]} {retrievedAt.split("T")[1]?.slice(0, 8)}
            </span>
          </div>

          {/* Evidence Source Chips */}
          <div className="flex flex-wrap items-center gap-1.5 mt-1">
            <span className="text-slate-500 text-[11px]">Evidence:</span>
            {line.evidence_ids.length === 0 ? (
              <span className="text-slate-600 font-mono text-[11px]">none</span>
            ) : (
              line.evidence_ids.map((eid) => {
                const ev = evidenceMap[eid];
                return (
                  <button
                    key={eid}
                    onClick={() => ev && onOpenEvidence(ev)}
                    className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-mono font-medium bg-sky-950/80 hover:bg-sky-900 text-sky-300 hover:text-white border border-sky-800 transition-colors cursor-pointer"
                    title={ev ? `${ev.source_endpoint} → ${ev.field_path || "record"}` : eid}
                  >
                    <Database className="w-3 h-3 text-sky-400" />
                    <span>{eid}</span>
                  </button>
                );
              })
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
