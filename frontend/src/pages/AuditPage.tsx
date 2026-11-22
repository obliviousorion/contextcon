import { useRef, useState, type FormEvent } from "react";
import { api, errorMessage } from "../lib/api";
import { normalizeDomainInput } from "../lib/format";
import { useHealth } from "../lib/health";
import { isSpendGate, type AuditReport, type ClaimInput, type JsonValue, type SpendGate } from "../types";
import { SpendConfirm } from "../components/SpendConfirm";
import { ApprovalStepper } from "../components/ApprovalStepper";
import { ClaimRows, type ClaimDraft } from "../components/ClaimRows";
import { ErrorState, ListSkeleton, PageTitle } from "../components/States";
import { VerdictTable } from "../components/VerdictTable";

function parseValue(s: string): JsonValue | null {
  const t = s.trim();
  if (!t) return null;
  const n = Number(t);
  return Number.isFinite(n) ? n : t;
}

export default function AuditPage() {
  const { today } = useHealth();
  const nextKey = useRef(2);
  const [domain, setDomain] = useState("tciexpress.in");
  const [rows, setRows] = useState<ClaimDraft[]>([
    { key: 1, field: "headcount_growth", value: "4", as_of: today, text: "grew 4x since 2019" },
  ]);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<{ report: AuditReport; text: Record<string, string> } | null>(null);
  const [gate, setGate] = useState<SpendGate | null>(null);

  const run = async (e?: FormEvent, confirm = false) => {
    e?.preventDefault();
    if (pending) return;
    const claims: ClaimInput[] = rows.map((r, i) => ({
      id: `c${i + 1}`, text: r.text.trim(), field: r.field.trim(), value: parseValue(r.value), as_of: r.as_of || null,
    }));
    setPending(true);
    setError(null);
    try {
      const res = await api.audit(normalizeDomainInput(domain), claims, confirm);
      if (isSpendGate(res)) {
        setGate(res);
        setResult(null);
        return;
      }
      setGate(null);
      setResult({ report: res.report, text: Object.fromEntries(claims.map((c) => [c.id, c.text])) });
    } catch (err) {
      setError(errorMessage(err));
      setResult(null);
    } finally {
      setPending(false);
    }
  };

  const add = () => setRows([...rows, { key: nextKey.current++, field: "headcount", value: "", as_of: today, text: "" }]);

  return (
    <div className="mx-auto max-w-file space-y-5">
      <PageTitle title="Audit claims">
        Check what a counterparty says about itself. Each claim gets agree, contradict or cannot verify, with the
        record line it rests on.
      </PageTitle>

      <form onSubmit={run} className="surface space-y-4 p-5">
        <div className="max-w-sm">
          <label htmlFor="audit-domain" className="label">Company domain</label>
          <input id="audit-domain" className="input font-mono" value={domain} required
            onChange={(e) => setDomain(e.target.value)} disabled={pending} />
        </div>
        <ClaimRows rows={rows} onChange={setRows} disabled={pending} />
        <div className="flex flex-wrap gap-2">
          <button type="button" className="btn-secondary" onClick={add} disabled={pending}>Add a claim</button>
          <button type="submit" className="btn-primary" disabled={pending || !domain.trim()}>
            {pending ? "Auditing…" : "Audit claims"}
          </button>
        </div>
      </form>

      <div aria-live="polite">
        {pending ? <ListSkeleton rows={rows.length} label="Auditing" />
          : error ? <ErrorState message={error} onRetry={() => void run()} title="The audit failed" />
          : gate ? <SpendConfirm gate={gate} what={`the record for ${normalizeDomainInput(domain)}`}
              onConfirm={() => void run(undefined, true)} onCancel={() => setGate(null)} />
          : result && (
            <div className="space-y-5">
              <VerdictTable report={result.report} claimText={result.text} />
              <ApprovalStepper key={result.report.id} id={result.report.id} status={result.report.status} noun="audit report" />
            </div>
          )}
      </div>
    </div>
  );
}
