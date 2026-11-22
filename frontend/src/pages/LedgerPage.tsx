import { Link } from "react-router-dom";
import { api } from "../lib/api";
import { fmtCredits, fmtInr } from "../lib/format";
import { useAsync } from "../lib/useAsync";
import { EmptyState, ErrorState, ListSkeleton, PageTitle } from "../components/States";

export default function LedgerPage() {
  const state = useAsync((signal) => api.cost(signal), []);

  return (
    <div className="mx-auto max-w-file">
      <PageTitle title="Ledger">
        What this run spent against what each stored file measured when its copies were recorded live. Credits are
        Crustdata's unit; rupees at the configured rate.
      </PageTitle>
      {state.status === "loading" ? <ListSkeleton rows={3} label="Loading the ledger" />
        : state.status === "error" ? <ErrorState message={state.error} onRetry={state.retry} />
        : (
          <div className="space-y-5">
            <section className="surface" aria-labelledby="totals-head">
              <h2 id="totals-head" className="border-b border-line px-5 py-3 text-lg">Totals</h2>
              <dl className="divide-y divide-line">
                <div className="flex flex-wrap justify-between gap-2 px-5 py-3">
                  <dt>Spent this run (ledger)</dt>
                  <dd className="font-mono">{fmtCredits(state.data.ledger_credits_spent)} · {fmtInr(state.data.ledger_inr_spent)}</dd>
                </div>
                <div className="flex flex-wrap justify-between gap-2 px-5 py-3">
                  <dt>Measured cost of all stored copies</dt>
                  <dd className="font-mono">{fmtCredits(state.data.total_recorded_credits)}</dd>
                </div>
              </dl>
            </section>

            {state.data.case_files.length === 0 ? (
              <EmptyState title="No case files yet">Nothing has been built in this state directory.</EmptyState>
            ) : (
              <section className="surface" aria-labelledby="per-file-head">
                <h2 id="per-file-head" className="border-b border-line px-5 py-3 text-lg">Per file</h2>
                <div className="overflow-x-auto">
                  <table className="w-full min-w-[34rem] text-left text-sm">
                    <thead className="border-b border-line text-meta text-muted">
                      <tr>
                        <th scope="col" className="px-5 py-2 font-medium">File</th>
                        <th scope="col" className="px-3 py-2 font-medium">Domain</th>
                        <th scope="col" className="px-3 py-2 text-right font-medium">This run</th>
                        <th scope="col" className="px-5 py-2 text-right font-medium">Measured</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-line">
                      {state.data.case_files.map((r) => (
                        <tr key={r.id}>
                          <td className="px-5 py-2.5">
                            <Link to={`/files/${r.id}`} className="btn-link font-mono">{r.id}</Link>
                            <div className="text-meta text-muted">{r.kind}</div>
                          </td>
                          <td className="px-3 py-2.5 font-mono">{r.domain ?? "unknown"}</td>
                          <td className="px-3 py-2.5 text-right font-mono">{fmtInr(r.inr)}<div className="text-meta text-muted">{fmtCredits(r.credits)}</div></td>
                          <td className="px-5 py-2.5 text-right font-mono">{fmtInr(r.recorded_inr)}<div className="text-meta text-muted">{fmtCredits(r.recorded_credits)}</div></td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </section>
            )}
            <p className="text-meta text-muted">
              A watcher alert costs 5 credits and is passed through at cost. Limits: 40 credits and 300 seconds per run.
            </p>
          </div>
        )}
    </div>
  );
}
