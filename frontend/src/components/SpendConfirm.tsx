import { fmtCredits, fmtInr } from "../lib/format";
import type { SpendGate } from "../types";

/**
 * Shown when a live server has no stored copy for this request. Nothing has been spent yet:
 * only the button below sends the request to Crustdata, and the response is cached afterwards.
 */
export function SpendConfirm({ gate, what, onConfirm, onCancel, pending = false }:
  { gate: SpendGate; what: string; onConfirm: () => void; onCancel?: () => void; pending?: boolean }) {
  const over = gate.estimate_credits > gate.session_left_credits;
  return (
    <section className="surface p-5" aria-labelledby="spend-title" role="region">
      <h2 id="spend-title" className="font-serif text-lg font-semibold text-ink">Live lookup needed</h2>
      <p className="mt-2 text-ink">
        {gate.reason} Nothing has been spent. Fetching {what} costs about{" "}
        <strong className="font-mono">{fmtCredits(gate.estimate_credits)}</strong>{" "}
        (<span className="font-mono">{fmtInr(gate.estimate_inr)}</span>).
      </p>
      <dl className="mt-3 grid grid-cols-[auto_1fr] gap-x-4 gap-y-1 text-meta text-muted">
        <dt>Estimate basis</dt><dd className="text-ink">{gate.basis}</dd>
        <dt>Session budget left</dt>
        <dd className="font-mono text-ink">{fmtCredits(gate.session_left_credits)} of {fmtCredits(gate.session_cap_credits)}</dd>
        <dt>After this</dt><dd className="text-ink">The response is stored, so the same company is never paid for twice.</dd>
      </dl>
      <div className="mt-4 flex flex-wrap gap-3">
        <button type="button" className="btn-primary" onClick={onConfirm} disabled={pending || over}
          aria-describedby="spend-title">
          {pending ? "Fetching…" : `Spend about ${fmtCredits(gate.estimate_credits)} and fetch`}
        </button>
        {onCancel && <button type="button" className="btn-secondary" onClick={onCancel} disabled={pending}>Cancel</button>}
      </div>
      {over && (
        <p className="mt-3 text-meta text-refuse" role="alert">
          The estimate is more than the session budget left. Restart the API server with a higher <code>--cap</code>.
        </p>
      )}
    </section>
  );
}
