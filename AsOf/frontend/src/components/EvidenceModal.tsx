import React from "react";
import { Evidence } from "../types";
import { X, FileText, Database, Calendar, Clock, ExternalLink } from "lucide-react";

interface EvidenceModalProps {
  evidence: Evidence | null;
  onClose: () => void;
}

export const EvidenceModal: React.FC<EvidenceModalProps> = ({
  evidence,
  onClose,
}) => {
  if (!evidence) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/75 backdrop-blur-sm animate-fade-in"
      onClick={onClose}
    >
      <div
        className="bg-slate-900 border border-slate-700 rounded-xl max-w-xl w-full p-6 shadow-2xl overflow-hidden relative"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between pb-4 mb-4 border-b border-slate-800">
          <div className="flex items-center gap-2.5">
            <span className="px-2.5 py-1 rounded bg-sky-950 text-sky-400 border border-sky-800 font-mono text-xs font-bold">
              {evidence.id}
            </span>
            <div className="flex items-center gap-1.5 text-sm font-semibold text-slate-200">
              <FileText className="w-4 h-4 text-sky-400" />
              <span>Evidence Artifact</span>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Metadata Details */}
        <div className="space-y-3 mb-5 text-xs text-slate-300">
          <div className="grid grid-cols-2 gap-3 bg-slate-950/60 p-3 rounded-lg border border-slate-800/80">
            <div>
              <span className="text-slate-500 block mb-0.5">Kind</span>
              <span className="font-mono text-slate-200">{evidence.kind}</span>
            </div>
            <div>
              <span className="text-slate-500 block mb-0.5">Source Endpoint</span>
              <span className="font-mono text-cyan-400 flex items-center gap-1">
                <Database className="w-3 h-3" />
                {evidence.source_endpoint}
              </span>
            </div>
            {evidence.field_path && (
              <div className="col-span-2">
                <span className="text-slate-500 block mb-0.5">Field Path</span>
                <span className="font-mono text-amber-300 text-[11px] break-all">
                  {evidence.field_path}
                </span>
              </div>
            )}
            {evidence.point_date && (
              <div>
                <span className="text-slate-500 block mb-0.5">Point Date</span>
                <span className="font-mono text-slate-200 flex items-center gap-1">
                  <Calendar className="w-3 h-3 text-slate-400" />
                  {evidence.point_date}
                </span>
              </div>
            )}
            <div>
              <span className="text-slate-500 block mb-0.5">Retrieved At</span>
              <span className="font-mono text-slate-200 flex items-center gap-1">
                <Clock className="w-3 h-3 text-slate-400" />
                {evidence.retrieved_at}
              </span>
            </div>
          </div>

          {evidence.url && (
            <div className="text-xs">
              <a
                href={evidence.url}
                target="_blank"
                rel="noreferrer"
                className="text-sky-400 hover:underline flex items-center gap-1"
              >
                <ExternalLink className="w-3 h-3" />
                {evidence.url}
              </a>
            </div>
          )}
        </div>

        {/* Verbatim Excerpt */}
        <div>
          <label className="text-xs font-semibold tracking-wider uppercase text-slate-400 block mb-2">
            Verbatim Excerpt / Record Slice
          </label>
          <pre className="p-3.5 rounded-lg bg-slate-950 border border-slate-800 text-xs font-mono text-slate-200 overflow-x-auto whitespace-pre-wrap max-h-56 leading-relaxed">
            {evidence.excerpt}
          </pre>
        </div>

        {/* Footer */}
        <div className="mt-5 pt-3 border-t border-slate-800 flex justify-end">
          <button
            onClick={onClose}
            className="px-4 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-medium transition-colors"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
};
