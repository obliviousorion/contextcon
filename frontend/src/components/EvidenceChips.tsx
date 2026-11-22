import type { Evidence } from "../types";

interface Props {
  ids: string[];
  evidence: Record<string, Evidence>;
  onOpen: (e: Evidence) => void;
}

export function EvidenceChips({ ids, evidence, onOpen }: Props) {
  if (ids.length === 0) return <span className="text-meta text-muted">No evidence cited</span>;
  return (
    <span className="inline-flex flex-wrap items-center gap-1.5">
      <span className="text-meta text-muted">Evidence</span>
      {ids.map((id) => {
        const ev = evidence[id];
        if (!ev) {
          return <span key={id} className="tag font-mono" title="Not included in this response">{id}</span>;
        }
        return (
          <button
            key={id}
            type="button"
            onClick={() => onOpen(ev)}
            className="rounded border border-accent bg-accent-tint px-1.5 py-px font-mono text-meta text-accent hover:bg-surface"
            aria-label={`Open evidence ${id}: ${ev.source_endpoint}${ev.field_path ? `, ${ev.field_path}` : ""}`}
            aria-haspopup="dialog"
          >
            {id}
          </button>
        );
      })}
    </span>
  );
}
