import { useRef, useState } from "react";
import type { EvidenceRequest } from "../types";
import { api, errorMessage, evidenceRequestId } from "../lib/api";
import { ApprovalStepper } from "./ApprovalStepper";

/** A held request to the counterparty. It records what is missing; it is never a rejection. */
export function EvidenceRequestCard({ request, stored = false }: { request: EvidenceRequest; stored?: boolean }) {
  const id = evidenceRequestId(request);
  const saved = useRef(stored);
  const [error, setError] = useState<string | null>(null);

  // The case file embeds the request; POST /api/evidence_request stores it under the same id.
  const prepare = async () => {
    if (saved.current) return;
    setError(null);
    try {
      await api.evidenceRequest(request.target, request.items);
      saved.current = true;
    } catch (e) {
      setError(errorMessage(e));
      throw e;
    }
  };

  return (
    <section className="surface" aria-labelledby={`er-${id}`}>
      <div className="border-b border-line p-5">
        <span className="chip bg-sunken text-ink">Not a negative finding</span>
        <h2 id={`er-${id}`} className="mt-2 text-lg">Evidence request to {request.target}</h2>
        <p className="mt-1 text-muted">
          The records cannot settle every line. This asks the counterparty for documents; it says nothing against them.
        </p>
        <ul className="mt-3 list-disc space-y-1 pl-5 text-ink">
          {request.items.map((it) => <li key={it}>{it}</li>)}
        </ul>
        <p className="mt-2 font-mono text-meta text-muted">{id}</p>
      </div>
      <div className="p-5 pt-2">
        <ApprovalStepper id={id} status={request.status} noun="request" prepare={prepare} compact />
        {error && <p role="alert" className="mt-2 text-sm text-danger">Could not store the request: {error}</p>}
      </div>
    </section>
  );
}
