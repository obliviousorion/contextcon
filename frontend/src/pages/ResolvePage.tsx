import { useState } from "react";
import { Navigate, useNavigate, useSearchParams } from "react-router-dom";
import { api } from "../lib/api";
import { normalizeDomainInput } from "../lib/format";
import { useAsync } from "../lib/useAsync";
import { isSpendGate, type ResolveResult, type SpendGate } from "../types";
import { SpendConfirm } from "../components/SpendConfirm";
import { CandidateList } from "../components/CandidateList";
import { SearchBox } from "../components/SearchBox";
import { EmptyState, ErrorState, ListSkeleton, PageTitle } from "../components/States";

export default function ResolvePage() {
  const [params] = useSearchParams();
  const q = (params.get("q") ?? "").trim();
  const navigate = useNavigate();
  const [confirmedFor, setConfirmedFor] = useState<string | null>(null);
  const confirmed = confirmedFor === q;
  const state = useAsync<ResolveResult | SpendGate | null>(
    async (signal) => {
      if (!q) return null;
      const res = await api.casefile("resolve", q, undefined, signal, confirmed);
      if (isSpendGate(res)) return res;
      if ("resolve" in res) return res.resolve;
      return res.caseFile.resolve;
    },
    [q, confirmed],
  );

  return (
    <div className="mx-auto max-w-file">
      <PageTitle title="Resolve a company">
        A name can match many companies. AsOf lists every candidate and lets you choose a domain.
      </PageTitle>
      <div className="mb-6"><SearchBox key={q} initial={q} /></div>
      {!q ? (
        <EmptyState title="Enter a name or a domain">For example “Shree Balaji Logistics”.</EmptyState>
      ) : state.status === "loading" ? (
        <ListSkeleton rows={4} label="Resolving" />
      ) : state.status === "error" ? (
        <ErrorState message={state.error} onRetry={state.retry} />
      ) : isSpendGate(state.data) ? (
        <SpendConfirm gate={state.data} what={`the candidates for “${q}”`}
          onConfirm={() => setConfirmedFor(q)} onCancel={() => navigate("/")} />
      ) : state.data && state.data.status === "resolved" && state.data.entity ? (
        <Navigate to={`/clear/${encodeURIComponent(normalizeDomainInput(q))}`} replace />
      ) : state.data ? (
        <div aria-live="polite"><CandidateList resolve={state.data} query={q} /></div>
      ) : null}
    </div>
  );
}
