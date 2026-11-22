import { Link } from "react-router-dom";
import { api } from "../lib/api";
import { fmtCredits, fmtInr } from "../lib/format";
import { useAsync } from "../lib/useAsync";
import { isCaseFile, type CostFileRow, type FileDetail } from "../types";
import { EmptyState, ErrorState, ListSkeleton, PageTitle } from "../components/States";

type Row = CostFileRow & { detail: FileDetail | null };

function statusText(d: FileDetail | null): { text: string; cls: string } {
  if (!d) return { text: "unknown", cls: "bg-sunken text-muted" };
  const s = isCaseFile(d.artifact) ? d.artifact.status : "draft";
  if (d.stale.length) return { text: "Stale", cls: "bg-stale-tint text-stale" };
  if (s === "issued_sandbox") return { text: "Issued (sandbox)", cls: "bg-ok-tint text-ok" };
  if (s === "approved" || d.approval) return { text: "Approved", cls: "bg-ok-tint text-ok" };
  return { text: "Draft", cls: "bg-sunken text-ink" };
}

export default function FilesPage() {
  // /api/cost lists stored case files; their status needs one /api/files/{id} read each.
  const state = useAsync<Row[]>(async (signal) => {
    const cost = await api.cost(signal);
    return Promise.all(cost.case_files.map(async (r) => ({
      ...r, detail: await api.file(r.id, signal).catch(() => null),
    })));
  }, []);

  return (
    <div className="mx-auto max-w-file">
      <PageTitle title="Case files">Every stored clearance and dispute file, with its status and cost.</PageTitle>
      {state.status === "loading" ? <ListSkeleton rows={4} label="Loading files" />
        : state.status === "error" ? <ErrorState message={state.error} onRetry={state.retry} />
        : state.data.length === 0 ? (
          <EmptyState title="No case files yet">
            Build one from <Link to="/" className="btn-link">Home</Link>; it is stored as a draft.
          </EmptyState>
        ) : (
          <ul className="surface divide-y divide-line" aria-label="Stored case files">
            {state.data.map((r) => {
              const st = statusText(r.detail);
              const asOf = r.detail && isCaseFile(r.detail.artifact) ? r.detail.artifact.request.as_of : undefined;
              return (
                <li key={r.id} className="flex flex-wrap items-center gap-x-5 gap-y-2 px-5 py-4">
                  <div className="min-w-0 flex-1">
                    <Link to={`/files/${r.id}`} className="font-mono text-[15px] font-medium text-accent underline underline-offset-2">
                      {r.id}
                    </Link>
                    <p className="text-ink">
                      <span className="font-mono text-sm">{r.domain ?? "unknown"}</span>
                      <span className="text-muted"> · {r.kind}{asOf && <> as of <span className="font-mono">{asOf}</span></>}</span>
                    </p>
                  </div>
                  <span className={`chip ${st.cls}`}>{st.text}</span>
                  <div className="text-right text-sm">
                    <p className="font-mono">{fmtInr(r.inr)} <span className="text-muted">this run</span></p>
                    <p className="font-mono text-muted">{fmtInr(r.recorded_inr)} measured · {fmtCredits(r.recorded_credits)}</p>
                  </div>
                </li>
              );
            })}
          </ul>
        )}
    </div>
  );
}
