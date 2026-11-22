import React from "react";
import { CostSummary } from "../types";
import { Coins, IndianRupee, Layers, CheckCircle2 } from "lucide-react";

interface CostPanelProps {
  cost: CostSummary;
}

export const CostPanel: React.FC<CostPanelProps> = ({ cost }) => {
  return (
    <div className="bg-slate-900/90 border border-slate-800 rounded-xl p-4 shadow-sm backdrop-blur">
      <div className="flex items-center justify-between pb-3 mb-3 border-b border-slate-800/80">
        <div className="flex items-center gap-2">
          <Coins className="w-4 h-4 text-amber-400" />
          <span className="text-xs font-semibold tracking-wider uppercase text-slate-400">
            Cost & Ledger Panel
          </span>
        </div>
        <span className="text-xs text-slate-500 font-mono">
          {cost.cost_note ?? "Measured from ledger"}
        </span>
      </div>

      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        {/* Spent this run */}
        <div className="bg-slate-950/60 rounded-lg p-3 border border-slate-800/60">
          <div className="text-xs text-slate-400 flex items-center gap-1.5 mb-1">
            <Coins className="w-3.5 h-3.5 text-amber-400" />
            <span>Spent this run</span>
          </div>
          <div className="text-lg font-bold font-mono text-slate-100">
            {cost.credits.toFixed(2)} cr · ₹{cost.inr.toFixed(2)}
          </div>
          <div className="text-[11px] text-slate-500 mt-0.5">
            {cost.calls === 0 ? "replay: served from stored copies" : "live Crustdata calls"}
          </div>
        </div>

        {/* Recorded cost of the stored copies (measured, from the recorded ledger) */}
        <div className="bg-slate-950/60 rounded-lg p-3 border border-slate-800/60">
          <div className="text-xs text-slate-400 flex items-center gap-1.5 mb-1">
            <IndianRupee className="w-3.5 h-3.5 text-emerald-400" />
            <span>Measured cost of this file</span>
          </div>
          <div className="text-lg font-bold font-mono text-emerald-400">
            ₹{(cost.recorded_inr ?? cost.inr).toFixed(2)}
          </div>
          <div className="text-[11px] text-slate-500 mt-0.5">
            {(cost.recorded_credits ?? cost.credits).toFixed(2)} credits, from the recorded ledger
          </div>
        </div>

        {/* API Calls */}
        <div className="bg-slate-950/60 rounded-lg p-3 border border-slate-800/60">
          <div className="text-xs text-slate-400 flex items-center gap-1.5 mb-1">
            <Layers className="w-3.5 h-3.5 text-blue-400" />
            <span>API Calls</span>
          </div>
          <div className="text-lg font-bold font-mono text-slate-100">
            {cost.calls}
          </div>
          <div className="text-[11px] text-slate-500 mt-0.5">
            endpoints invoked
          </div>
        </div>

        {/* Cache Hits */}
        <div className="bg-slate-950/60 rounded-lg p-3 border border-slate-800/60">
          <div className="text-xs text-slate-400 flex items-center gap-1.5 mb-1">
            <CheckCircle2 className="w-3.5 h-3.5 text-cyan-400" />
            <span>Cache Hits</span>
          </div>
          <div className="text-lg font-bold font-mono text-slate-100">
            {cost.cache_hits}
          </div>
          <div className="text-[11px] text-slate-500 mt-0.5">
            replayed from cache
          </div>
        </div>
      </div>
    </div>
  );
};
