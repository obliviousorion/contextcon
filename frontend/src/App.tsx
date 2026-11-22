import React, { useState } from "react";
import { CaseFile, Evidence, ResolveResult, ToolType } from "./types";
import { FIXTURE_OUTCOMES, fetchCaseFileData } from "./data";
import { RequestBar } from "./components/RequestBar";
import { DateSlider } from "./components/DateSlider";
import { CaseFileLine } from "./components/CaseFileLine";
import { CostPanel } from "./components/CostPanel";
import { ApproveButton } from "./components/ApproveButton";
import { EvidenceModal } from "./components/EvidenceModal";
import { ResolveResultView } from "./components/ResolveResultView";
import {
  FileCheck2,
  Calendar,
  AlertCircle,
  Clock,
  Layers,
} from "lucide-react";

export const App: React.FC = () => {
  // Active fixture index for date slider
  const [sliderIndex, setSliderIndex] = useState<number>(2); // Default to Clearance (2026-11-22)
  const currentOutcome = FIXTURE_OUTCOMES[sliderIndex] || FIXTURE_OUTCOMES[0];

  // Request bar state
  const [tool, setTool] = useState<ToolType>(currentOutcome.tool);
  const [domain, setDomain] = useState<string>(currentOutcome.domain);
  const [asOf, setAsOf] = useState<string>(currentOutcome.date);
  const [isLoading, setIsLoading] = useState<boolean>(false);

  // Active case file & resolve state
  const [activeCaseFile, setActiveCaseFile] = useState<CaseFile | undefined>(currentOutcome.caseFile);
  const [activeResolve, setActiveResolve] = useState<ResolveResult | undefined>(
    currentOutcome.resolveResult || currentOutcome.caseFile?.resolve
  );

  // Evidence modal state
  const [selectedEvidence, setSelectedEvidence] = useState<Evidence | null>(null);

  // Sync state when moving the date slider
  const handleSelectOutcome = (index: number) => {
    setSliderIndex(index);
    const outcome = FIXTURE_OUTCOMES[index];
    if (outcome) {
      setTool(outcome.tool);
      setDomain(outcome.domain);
      setAsOf(outcome.date);
      setActiveCaseFile(outcome.caseFile);
      setActiveResolve(outcome.resolveResult || outcome.caseFile?.resolve);
    }
  };

  // Run query / fetch handler
  const [queryError, setQueryError] = useState<string | null>(null);
  const handleQuery = async () => {
    setIsLoading(true);
    setQueryError(null);
    try {
      const result = await fetchCaseFileData(tool, domain, asOf);
      if (result.caseFile) {
        setActiveCaseFile(result.caseFile);
        setActiveResolve(result.caseFile.resolve);
      } else if (result.resolve) {
        setActiveResolve(result.resolve);
        setActiveCaseFile(undefined);
      }
    } catch (err) {
      console.error("Failed to query case file:", err);
      setQueryError((err as Error).message);
    } finally {
      setIsLoading(false);
    }
  };

  const attestation = activeCaseFile?.attestation;
  const entity = activeCaseFile?.resolve.entity || attestation?.entity;

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 selection:bg-sky-500/30">
      {/* Evidence Modal */}
      <EvidenceModal
        evidence={selectedEvidence}
        onClose={() => setSelectedEvidence(null)}
      />

      {/* Top Navbar */}
      <header className="border-b border-slate-800 bg-slate-900/60 backdrop-blur sticky top-0 z-40">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-lg bg-sky-500/10 border border-sky-500/30 flex items-center justify-center text-sky-400 font-bold font-mono">
              As
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="font-bold text-lg text-slate-100 tracking-tight">AsOf</span>
                <span className="text-[11px] font-mono font-medium px-2 py-0.5 rounded-full bg-slate-800 text-sky-300 border border-slate-700">
                  provable company facts
                </span>
              </div>
              <p className="text-[11px] text-slate-400 hidden sm:block">
                Deciding what records swear to, and as of when.
              </p>
            </div>
          </div>

          <div className="flex items-center gap-3">
            <div className="hidden md:flex items-center gap-2 text-xs text-slate-400 font-mono bg-slate-900 px-3 py-1.5 rounded-lg border border-slate-800">
              <span className="w-2 h-2 rounded-full bg-emerald-400"></span>
              <span>Replay Engine: Active</span>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content Area */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-6">
        {/* Date Slider Section */}
        <DateSlider
          outcomes={FIXTURE_OUTCOMES}
          currentIndex={sliderIndex}
          onSelectIndex={handleSelectOutcome}
        />

        {/* Request Bar */}
        <RequestBar
          tool={tool}
          domain={domain}
          asOf={asOf}
          onChangeTool={setTool}
          onChangeDomain={setDomain}
          onChangeAsOf={setAsOf}
          onSubmit={handleQuery}
          isLoading={isLoading}
        />

        {import.meta.env.VITE_API_URL ? (
          <div className="text-xs text-emerald-300/80">Live backend: {import.meta.env.VITE_API_URL} (replay mode, 0 credits)</div>
        ) : (
          <div className="text-xs text-slate-500">Fixture mode: recorded outcomes only. Set VITE_API_URL to call the real backend.</div>
        )}
        {queryError && (
          <div className="rounded-lg border border-rose-800/80 bg-rose-950/60 px-4 py-2 text-sm text-rose-200">{queryError}</div>
        )}

        {/* Resolve Refusal View (when tool is resolve or resolve failed) */}
        {(tool === "resolve" || (!activeCaseFile && activeResolve)) && activeResolve && (
          <div className="space-y-6">
            <ResolveResultView
              resolve={activeResolve}
              targetName={domain || "Shree Balaji Logistics"}
            />
          </div>
        )}

        {/* Case File View */}
        {activeCaseFile && (
          <div className="space-y-6">
            {/* Case File Header Card */}
            <div className="bg-slate-900/90 border border-slate-800 rounded-xl p-5 shadow-sm">
              <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-4 mb-4 border-b border-slate-800">
                <div className="flex items-center gap-3">
                  <div className="p-2.5 rounded-lg bg-sky-950 text-sky-400 border border-sky-800">
                    <FileCheck2 className="w-6 h-6" />
                  </div>
                  <div>
                    <div className="flex items-center gap-2">
                      <h2 className="text-xl font-bold text-slate-100">
                        {entity?.name || "Target Entity"}
                      </h2>
                      <span className="text-xs font-mono px-2 py-0.5 rounded bg-slate-800 text-slate-300 border border-slate-700 uppercase">
                        {activeCaseFile.kind}
                      </span>
                      <span className="text-xs font-mono text-slate-400">
                        #{activeCaseFile.id}
                      </span>
                    </div>
                    <div className="flex flex-wrap items-center gap-3 text-xs text-slate-400 mt-1">
                      {entity && (
                        <>
                          <span className="flex items-center gap-1 font-mono text-cyan-400">
                            Crustdata ID: #{entity.crustdata_company_id}
                          </span>
                          <span>•</span>
                          <span className="font-mono">
                            Domains: {entity.domains.join(", ") || "none"}
                          </span>
                          <span>•</span>
                          <span className="text-slate-500">
                            Resolved by {entity.resolved_by}
                          </span>
                        </>
                      )}
                    </div>
                  </div>
                </div>

                {/* Approve & Issue Action */}
                <div className="flex items-center gap-2 self-start md:self-auto">
                  <ApproveButton
                    key={activeCaseFile.id}
                    caseId={activeCaseFile.id}
                    initialStatus={activeCaseFile.status}
                    onApproved={() => console.log("Case file approved & issued to sandbox")}
                  />
                </div>
              </div>

              {/* Case Summary Bar */}
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 text-xs bg-slate-950/60 p-3 rounded-lg border border-slate-800/80">
                <div className="flex items-center gap-2">
                  <Calendar className="w-4 h-4 text-sky-400" />
                  <span className="text-slate-400">As-Of Date:</span>
                  <span className="font-mono font-bold text-slate-200">
                    {attestation?.as_of || activeCaseFile.request.as_of || asOf}
                  </span>
                </div>
                <div className="flex items-center gap-2">
                  <Clock className="w-4 h-4 text-slate-400" />
                  <span className="text-slate-400">Generated:</span>
                  <span className="font-mono text-slate-300">
                    {attestation?.generated_at?.split("T")[0] || "2026-11-22"}
                  </span>
                </div>
                <div className="flex items-center gap-2">
                  <Layers className="w-4 h-4 text-slate-400" />
                  <span className="text-slate-400">Attested Lines:</span>
                  <span className="font-mono text-emerald-400 font-bold">
                    {attestation?.lines.filter((l) => l.status === "attested").length || 0} /{" "}
                    {attestation?.lines.length || 0}
                  </span>
                </div>
              </div>
            </div>

            {/* Cost Panel */}
            <CostPanel cost={activeCaseFile.cost} />

            {/* Attested / Refused Lines Section */}
            <div className="space-y-3">
              <div className="flex items-center justify-between px-1">
                <h3 className="text-sm font-semibold tracking-wider uppercase text-slate-300 flex items-center gap-2">
                  <span>Attestation Findings</span>
                  <span className="text-xs font-mono font-normal text-slate-500">
                    ({attestation?.lines.length || 0} fields evaluated)
                  </span>
                </h3>
                <span className="text-xs text-slate-500">
                  Click any evidence chip to inspect stored raw records
                </span>
              </div>

              <div className="space-y-2.5">
                {attestation?.lines.map((line, idx) => (
                  <CaseFileLine
                    key={`${line.field}-${idx}`}
                    line={line}
                    evidenceMap={activeCaseFile.evidence}
                    onOpenEvidence={(ev) => setSelectedEvidence(ev)}
                  />
                ))}
              </div>
            </div>

            {/* Subsequent Events Section (if any exist) */}
            {attestation?.subsequent_events && attestation.subsequent_events.length > 0 && (
              <div className="space-y-3 pt-4">
                <div className="flex items-center gap-2 px-1">
                  <AlertCircle className="w-4 h-4 text-purple-400" />
                  <h3 className="text-sm font-semibold tracking-wider uppercase text-purple-300">
                    Subsequent Events (Dated After As-Of Date D — Never Attested)
                  </h3>
                </div>

                <div className="space-y-2.5">
                  {attestation.subsequent_events.map((line, idx) => (
                    <CaseFileLine
                      key={`subsequent-${line.field}-${idx}`}
                      line={line}
                      evidenceMap={activeCaseFile.evidence}
                      onOpenEvidence={(ev) => setSelectedEvidence(ev)}
                    />
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        {/* Footer Note */}
        <footer className="pt-8 pb-4 text-center text-xs text-slate-500 border-t border-slate-900 space-y-1">
          <p>
            AsOf • Replay & Sandbox Verification
          </p>
          <p className="text-[11px] text-slate-600">
            Costs are measured from the Crustdata ledger. The ₹600 price per cleared file is an <span className="text-slate-500 font-medium">(estimate)</span>.
          </p>
        </footer>
      </main>
    </div>
  );
};

export default App;
