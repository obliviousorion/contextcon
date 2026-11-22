import React from "react";
import { ToolType } from "../types";
import { Search, Globe, Calendar, ArrowRight, Check } from "lucide-react";

interface RequestBarProps {
  tool: ToolType;
  domain: string;
  asOf: string;
  onChangeTool: (tool: ToolType) => void;
  onChangeDomain: (domain: string) => void;
  onChangeAsOf: (asOf: string) => void;
  onSubmit: () => void;
  isLoading?: boolean;
}

const TOOLS: { id: ToolType; label: string; desc: string }[] = [
  { id: "clear", label: "Clear", desc: "Clearance file (today)" },
  { id: "dispute", label: "Dispute", desc: "Dispute file (date D)" },
  { id: "attest", label: "Attest", desc: "Attest single field" },
  { id: "resolve", label: "Resolve", desc: "Resolve company entity" },
];

export const RequestBar: React.FC<RequestBarProps> = ({
  tool,
  domain,
  asOf,
  onChangeTool,
  onChangeDomain,
  onChangeAsOf,
  onSubmit,
  isLoading = false,
}) => {
  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onSubmit();
  };

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-xl p-4 shadow-md">
      {/* Tool Selector Tabs */}
      <div className="flex flex-wrap items-center gap-2 mb-4 pb-3 border-b border-slate-800">
        <span className="text-xs font-semibold uppercase tracking-wider text-slate-400 mr-1">
          Tool:
        </span>
        {TOOLS.map((t) => {
          const isActive = tool === t.id;
          return (
            <button
              key={t.id}
              type="button"
              onClick={() => onChangeTool(t.id)}
              className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-all flex items-center gap-1.5 cursor-pointer ${
                isActive
                  ? "bg-sky-500 text-white shadow-sm shadow-sky-500/30"
                  : "bg-slate-800 text-slate-400 hover:text-slate-200 hover:bg-slate-700/80"
              }`}
            >
              {isActive && <Check className="w-3.5 h-3.5" />}
              <span>{t.label}</span>
              <span className="opacity-70 text-[10px] hidden sm:inline">({t.desc})</span>
            </button>
          );
        })}
      </div>

      {/* Input Controls Form */}
      <form onSubmit={handleSubmit} className="grid grid-cols-1 md:grid-cols-12 gap-3 items-end">
        {/* Domain Input */}
        <div className="md:col-span-5">
          <label className="block text-xs font-medium text-slate-300 mb-1.5 flex items-center gap-1">
            <Globe className="w-3.5 h-3.5 text-slate-400" />
            Domain / Counterparty
          </label>
          <div className="relative">
            <input
              type="text"
              value={domain}
              onChange={(e) => onChangeDomain(e.target.value)}
              placeholder="e.g. delhivery.com or tciexpress.in"
              className="w-full bg-slate-950 border border-slate-700 rounded-lg px-3 py-2 text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-sky-500/50 focus:border-sky-500"
            />
          </div>
        </div>

        {/* As-Of Date Input */}
        <div className="md:col-span-4">
          <label className="block text-xs font-medium text-slate-300 mb-1.5 flex items-center gap-1">
            <Calendar className="w-3.5 h-3.5 text-slate-400" />
            As-Of Date (D)
          </label>
          <input
            type="date"
            value={asOf}
            onChange={(e) => onChangeAsOf(e.target.value)}
            className="w-full bg-slate-950 border border-slate-700 rounded-lg px-3 py-2 text-sm font-mono text-slate-100 placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-sky-500/50 focus:border-sky-500"
          />
        </div>

        {/* Submit Button */}
        <div className="md:col-span-3">
          <button
            type="submit"
            disabled={isLoading}
            className="w-full bg-sky-600 hover:bg-sky-500 text-white rounded-lg px-4 py-2 text-sm font-semibold transition-all duration-150 flex items-center justify-center gap-2 cursor-pointer shadow-sm hover:shadow active:scale-98 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {isLoading ? (
              <span className="animate-spin rounded-full h-4 w-4 border-2 border-white border-t-transparent" />
            ) : (
              <>
                <Search className="w-4 h-4" />
                <span>Run {tool}</span>
                <ArrowRight className="w-3.5 h-3.5 opacity-70" />
              </>
            )}
          </button>
        </div>
      </form>
    </div>
  );
};
