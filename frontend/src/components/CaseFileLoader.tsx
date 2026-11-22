import { useState, type ReactNode } from "react";
import { Navigate, useNavigate } from "react-router-dom";
import { isCaseFile, isSpendGate, type CaseFile, type FileDetail, type SpendGate } from "../types";
import { api } from "../lib/api";
import { useAsync } from "../lib/useAsync";
import { CaseFileView } from "./CaseFileView";
import { SpendConfirm } from "./SpendConfirm";
import { ErrorState, ListSkeleton } from "./States";

type Loaded = { kind: "file"; cf: CaseFile; detail: FileDetail | null } | { kind: "name"; q: string }
  | { kind: "gate"; gate: SpendGate };

/**
 * Builds (or rebuilds) a case file, then reads its stored approval record and STALE marks.
 * Rebuilding saves a fresh draft, but the approval record survives, so it is shown from /api/files.
 */
export function CaseFileLoader({ tool, domain, asOf, controls }:
  { tool: "clear" | "dispute"; domain: string; asOf?: string; controls?: ReactNode }) {
  const navigate = useNavigate();
  // Confirmation is per request: changing the domain or date asks again.
  const reqKey = `${tool}|${domain}|${asOf ?? ""}`;
  const [confirmedFor, setConfirmedFor] = useState<string | null>(null);
  const confirmed = confirmedFor === reqKey;
  const state = useAsync<Loaded>(async (signal) => {
    const res = await api.casefile(tool, domain, asOf, signal, confirmed);
    if (isSpendGate(res)) return { kind: "gate", gate: res };
    if ("resolve" in res) return { kind: "name", q: domain };
    const detail = await api.file(res.caseFile.id, signal).catch(() => null);
    return { kind: "file", cf: res.caseFile, detail };
  }, [tool, domain, asOf, confirmed]);

  if (state.status === "loading") {
    return (
      <div className="mx-auto max-w-file space-y-5">
        {controls && <div className="surface p-5">{controls}</div>}
        <ListSkeleton rows={5} label={`Building the ${tool === "clear" ? "clearance" : "dispute"} file`} />
      </div>
    );
  }
  if (state.status === "error") {
    return (
      <div className="mx-auto max-w-file space-y-5">
        {controls && <div className="surface p-5">{controls}</div>}
        <ErrorState message={state.error} onRetry={state.retry} title="Could not build the case file" />
      </div>
    );
  }
  if (state.data.kind === "gate") {
    return (
      <div className="mx-auto max-w-file space-y-5">
        {controls && <div className="surface p-5">{controls}</div>}
        <SpendConfirm gate={state.data.gate} what={`the ${tool === "clear" ? "clearance" : "dispute"} file for ${domain}`}
          onConfirm={() => setConfirmedFor(reqKey)} onCancel={() => navigate("/")} />
      </div>
    );
  }
  if (state.data.kind === "name") return <Navigate to={`/resolve?q=${encodeURIComponent(state.data.q)}`} replace />;

  const { detail } = state.data;
  // The stored copy carries the STALE marks a watcher alert added; it is otherwise the same file.
  const cf = detail && isCaseFile(detail.artifact) && detail.artifact.id === state.data.cf.id
    ? detail.artifact : state.data.cf;
  const approval = detail?.approval ?? null;
  // A rebuilt file is saved as a draft; an existing approval record means it was approved before.
  const shown: CaseFile = approval && cf.status === "draft" ? { ...cf, status: "approved" } : cf;
  return (
    <div>
      <p className="sr-only" role="status">
        {cf.kind} file {cf.id} loaded: {cf.attestation ? `${cf.attestation.lines.length} lines` : "company not resolved"}.
      </p>
      <CaseFileView cf={shown} approval={approval} stale={detail?.stale ?? []} controls={controls} />
    </div>
  );
}
