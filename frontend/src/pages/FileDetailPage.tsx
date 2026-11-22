import { Link, useParams } from "react-router-dom";
import { api } from "../lib/api";
import { fmtDateTime } from "../lib/format";
import { useAsync } from "../lib/useAsync";
import { isAuditReport, isCaseFile, type FileDetail } from "../types";
import { ApprovalStepper } from "../components/ApprovalStepper";
import { CaseFileView } from "../components/CaseFileView";
import { EvidenceRequestCard } from "../components/EvidenceRequestCard";
import { ErrorState, ListSkeleton } from "../components/States";
import { VerdictTable } from "../components/VerdictTable";

function ApprovalRecordLine({ d }: { d: FileDetail }) {
  return (
    <p className="mx-auto mb-4 max-w-file text-sm text-ink">
      <span className="text-muted">Approval record: </span>
      {d.approval ? <>approved by <span className="font-medium">{d.approval.by}</span> at {fmtDateTime(d.approval.at)}</>
        : "not approved"}
    </p>
  );
}

export default function FileDetailPage() {
  const { id = "" } = useParams();
  const state = useAsync((signal) => api.file(id, signal), [id]);

  return (
    <>
      <nav aria-label="Breadcrumb" className="mx-auto mb-3 max-w-file text-sm">
        <Link to="/files" className="btn-link">Case files</Link>
        <span className="text-muted"> / </span><span className="font-mono">{id}</span>
      </nav>
      {state.status === "loading" ? <div className="mx-auto max-w-file"><ListSkeleton rows={5} label="Loading the file" /></div>
        : state.status === "error" ? (
          <div className="mx-auto max-w-file"><ErrorState message={state.error} onRetry={state.retry} title="Could not open this file" /></div>
        ) : (() => {
          const d = state.data;
          const a = d.artifact;
          if (isCaseFile(a)) {
            const shown = d.approval && a.status === "draft" ? { ...a, status: "approved" as const } : a;
            return (<><ApprovalRecordLine d={d} /><CaseFileView cf={shown} approval={d.approval} stale={d.stale} /></>);
          }
          if (isAuditReport(a)) {
            return (
              <div className="mx-auto max-w-file space-y-5">
                <ApprovalRecordLine d={d} />
                <VerdictTable report={a} />
                <ApprovalStepper id={a.id} status={a.status} approval={d.approval} noun="audit report" />
              </div>
            );
          }
          return (
            <div className="mx-auto max-w-file space-y-5">
              <ApprovalRecordLine d={d} />
              <EvidenceRequestCard request={a} stored />
            </div>
          );
        })()}
    </>
  );
}
