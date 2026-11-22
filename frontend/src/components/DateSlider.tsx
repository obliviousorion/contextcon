import React from "react";
import { FixtureOutcome } from "../types";
import { Sliders, Calendar, Building } from "lucide-react";

interface DateSliderProps {
  outcomes: FixtureOutcome[];
  currentIndex: number;
  onSelectIndex: (index: number) => void;
}

export const DateSlider: React.FC<DateSliderProps> = ({
  outcomes,
  currentIndex,
  onSelectIndex,
}) => {
  const current = outcomes[currentIndex] || outcomes[0];

  return (
    <div className="bg-slate-900/90 border border-slate-800 rounded-xl p-4 shadow-sm backdrop-blur">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 mb-3">
        <div className="flex items-center gap-2">
          <Sliders className="w-4 h-4 text-sky-400" />
          <span className="text-xs font-semibold tracking-wider uppercase text-slate-300">
            Move the date
          </span>
          <span className="text-xs text-slate-500">
            (Switch between fixture outcomes)
          </span>
        </div>

        <div className="flex items-center gap-2">
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md text-xs font-mono bg-sky-950/70 text-sky-300 border border-sky-800/60">
            <Calendar className="w-3.5 h-3.5 text-sky-400" />
            As of {current.date}
          </span>
          <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-md text-xs font-medium bg-slate-800 text-slate-300 border border-slate-700">
            <Building className="w-3.5 h-3.5 text-slate-400" />
            {current.companyName}
          </span>
        </div>
      </div>

      {/* Slider Control */}
      <div className="px-1 py-2">
        <input
          type="range"
          min={0}
          max={outcomes.length - 1}
          step={1}
          value={currentIndex}
          onChange={(e) => onSelectIndex(Number(e.target.value))}
          className="w-full h-2 bg-slate-800 rounded-lg appearance-none cursor-pointer accent-sky-400 focus:outline-none"
        />

        {/* Milestone Tick Marks */}
        <div className="flex justify-between mt-2.5">
          {outcomes.map((outcome, idx) => {
            const isSelected = idx === currentIndex;
            return (
              <button
                key={outcome.id}
                onClick={() => onSelectIndex(idx)}
                className={`flex flex-col items-center text-left transition-colors cursor-pointer group ${
                  isSelected ? "text-sky-300" : "text-slate-500 hover:text-slate-300"
                }`}
              >
                <span
                  className={`w-3 h-3 rounded-full mb-1 border-2 transition-all ${
                    isSelected
                      ? "bg-sky-400 border-sky-200 scale-125 ring-2 ring-sky-500/40"
                      : "bg-slate-700 border-slate-600 group-hover:bg-slate-500"
                  }`}
                />
                <span className="text-xs font-mono font-medium">{outcome.date}</span>
                <span className="text-[11px] font-sans opacity-80 hidden sm:inline-block max-w-[130px] truncate">
                  {outcome.title}
                </span>
              </button>
            );
          })}
        </div>
      </div>

      {/* Current Outcome Note */}
      <div className="mt-3 pt-3 border-t border-slate-800/80 text-xs text-slate-400 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="text-slate-500 font-medium">Scenario:</span>
          <span>{current.description}</span>
        </div>
        <span className="text-xs font-mono text-slate-500 uppercase tracking-wider">
          Tool: {current.tool}
        </span>
      </div>
    </div>
  );
};
