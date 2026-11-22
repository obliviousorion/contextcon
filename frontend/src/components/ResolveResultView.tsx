import React from "react";
import { ResolveResult } from "../types";
import { AlertTriangle, CheckCircle2, Building2, Globe, Hash, Info } from "lucide-react";

interface ResolveResultViewProps {
  resolve: ResolveResult;
  targetName?: string;
}

export const ResolveResultView: React.FC<ResolveResultViewProps> = ({
  resolve,
  targetName,
}) => {
  const isResolved = resolve.status === "resolved";

  return (
    <div className="bg-slate-900/90 border border-slate-800 rounded-xl p-5 shadow-sm">
      <div className="flex items-center justify-between pb-3 mb-4 border-b border-slate-800">
        <div className="flex items-center gap-2">
          {isResolved ? (
            <CheckCircle2 className="w-5 h-5 text-emerald-400" />
          ) : (
            <AlertTriangle className="w-5 h-5 text-amber-400" />
          )}
          <span className="text-sm font-bold text-slate-100">
            Resolution Status:{" "}
            <span
              className={`font-mono uppercase ${
                isResolved ? "text-emerald-400" : "text-amber-400"
              }`}
            >
              {resolve.status}
            </span>
          </span>
        </div>
        {targetName && (
          <span className="text-xs font-medium text-slate-400">
            Query: <span className="text-slate-200">"{targetName}"</span>
          </span>
        )}
      </div>

      {/* Refusal Notice */}
      {!isResolved && (
        <div className="bg-amber-950/40 border border-amber-900/70 p-4 rounded-lg mb-5 text-xs text-amber-200">
          <div className="flex items-center gap-2 font-semibold text-amber-300 mb-1">
            <Info className="w-4 h-4" />
            <span>CANNOT RESOLVE without disambiguating information</span>
          </div>
          <p className="text-slate-300">
            {resolve.missing
              ? `Missing: ${resolve.missing}. Multiple candidate records share this name.`
              : "A domain is required to resolve this entity to a unique record."}
          </p>
        </div>
      )}

      {/* Resolved Entity */}
      {isResolved && resolve.entity && (
        <div className="bg-slate-950/60 p-4 rounded-lg border border-slate-800/80 mb-5">
          <div className="text-xs font-semibold uppercase text-slate-400 mb-2">
            Resolved Entity
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 text-xs">
            <div>
              <span className="text-slate-500 block">Company Name</span>
              <span className="font-semibold text-slate-200">
                {resolve.entity.name || "N/A"}
              </span>
            </div>
            <div>
              <span className="text-slate-500 block">Crustdata ID</span>
              <span className="font-mono text-cyan-400">
                #{resolve.entity.crustdata_company_id}
              </span>
            </div>
            <div>
              <span className="text-slate-500 block">Domains</span>
              <span className="font-mono text-slate-300">
                {resolve.entity.domains.join(", ") || "none"}
              </span>
            </div>
          </div>
        </div>
      )}

      {/* Candidates List */}
      {resolve.candidates && resolve.candidates.length > 0 && (
        <div>
          <div className="flex items-center justify-between mb-2.5">
            <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">
              Candidates Found ({resolve.candidates.length})
            </span>
            <span className="text-[11px] text-slate-500">
              Requires a domain to settle
            </span>
          </div>

          <div className="space-y-2 max-h-72 overflow-y-auto pr-1">
            {resolve.candidates.map((cand, idx) => (
              <div
                key={cand.crustdata_company_id || idx}
                className="bg-slate-950 p-3 rounded-lg border border-slate-800/80 flex flex-col sm:flex-row sm:items-center justify-between gap-2 text-xs"
              >
                <div className="flex items-center gap-2">
                  <Building2 className="w-4 h-4 text-slate-500 shrink-0" />
                  <div>
                    <span className="font-medium text-slate-200">
                      {cand.name || "Unnamed entity"}
                    </span>
                    <div className="text-[11px] font-mono text-slate-400 flex items-center gap-2 mt-0.5">
                      <span className="flex items-center gap-1">
                        <Hash className="w-3 h-3 text-slate-500" />
                        ID: {cand.crustdata_company_id}
                      </span>
                      {cand.domains && cand.domains.length > 0 && (
                        <span className="flex items-center gap-1 text-sky-400">
                          <Globe className="w-3 h-3" />
                          {cand.domains.join(", ")}
                        </span>
                      )}
                    </div>
                  </div>
                </div>

                {cand.confidence !== null && cand.confidence !== undefined && (
                  <span className="font-mono text-xs px-2 py-0.5 rounded bg-slate-800 text-slate-300 border border-slate-700 self-start sm:self-auto">
                    Confidence: {(cand.confidence * 100).toFixed(0)}%
                  </span>
                )}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};
