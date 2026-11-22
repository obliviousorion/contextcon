import { Link } from "react-router-dom";
import type { ResolveResult } from "../types";

/** Refusal to pick a company: every candidate, never auto-selected. */
export function CandidateList({ resolve, query }: { resolve: ResolveResult; query: string }) {
  const n = resolve.candidates.length;
  return (
    <section className="surface" aria-labelledby="resolve-head">
      <div className="border-b border-line p-5">
        <p className="eyebrow">Refusal</p>
        <h2 id="resolve-head" className="text-xl">
          {n === 0 ? "Cannot resolve: no company matches" : `Cannot resolve: ${n} ${n === 1 ? "company matches" : "companies match"}`}
        </h2>
        <p className="mt-1 text-ink">
          AsOf will not choose for you. “<span className="font-mono text-sm">{query}</span>” does not point to exactly
          one company record.
        </p>
        {resolve.missing && (
          <p className="mt-2 rounded border border-line bg-refuse-tint px-3 py-2 text-ink">
            <span className="font-semibold">What would settle it: </span>{resolve.missing}
          </p>
        )}
      </div>
      {n > 0 && (
        <ul className="divide-y divide-line">
          {resolve.candidates.map((c) => (
            <li key={c.crustdata_company_id} className="flex flex-wrap items-center gap-x-4 gap-y-2 px-5 py-3">
              <div className="min-w-0 flex-1">
                <p className="font-medium text-ink">{c.name ?? "Unnamed record"}</p>
                <p className="font-mono text-meta text-muted">
                  id {c.crustdata_company_id}
                  {c.confidence != null && <> · confidence {c.confidence.toFixed(2)}</>}
                </p>
                <p className="break-all font-mono text-sm text-ink">
                  {c.domains.length ? c.domains.join(", ") : "no domain on record"}
                </p>
              </div>
              <div className="flex flex-wrap gap-2">
                {c.domains.map((d) => (
                  <Link key={d} to={`/clear/${encodeURIComponent(d)}`} className="btn-secondary py-1.5 text-sm">
                    Check {d}
                  </Link>
                ))}
              </div>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
