import type { ReactNode } from "react";
import type { Evidence } from "../types";
import { useFocusTrap } from "../lib/useFocusTrap";
import { CopyButton } from "./CopyButton";

interface Props {
  evidence: Evidence | null;
  onClose: () => void;
}

function Row({ term, children }: { term: string; children: ReactNode }) {
  return (
    <div className="border-b border-line py-2.5 last:border-0">
      <dt className="eyebrow">{term}</dt>
      <dd className="mt-0.5 break-all font-mono text-sm text-ink">{children}</dd>
    </div>
  );
}

/** Right-side drawer with the stored record behind one evidence chip. Esc closes; focus is trapped and returned. */
export function EvidenceDrawer({ evidence, onClose }: Props) {
  const ref = useFocusTrap<HTMLDivElement>(evidence !== null, onClose);
  if (!evidence) return null;
  const titleId = `ev-title-${evidence.id}`;

  return (
    <div className="fixed inset-0 z-drawer">
      <div className="scrim absolute inset-0" onClick={onClose} aria-hidden="true" />
      <div
        ref={ref}
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        className="drawer-in absolute inset-y-0 right-0 flex w-full max-w-md flex-col border-l border-line bg-surface"
      >
        <div className="flex items-start justify-between gap-3 border-b border-line px-5 py-4">
          <div>
            <p className="eyebrow">Evidence</p>
            <h2 id={titleId} className="text-xl">
              <span className="font-mono">{evidence.id}</span>{" "}
              <span className="text-muted">· {evidence.kind.replace(/_/g, " ")}</span>
            </h2>
          </div>
          <button type="button" onClick={onClose} className="btn-secondary px-2.5 py-1.5" data-autofocus>
            Close <span className="sr-only">evidence {evidence.id}</span>
            <kbd className="font-mono text-meta text-muted" aria-hidden="true">Esc</kbd>
          </button>
        </div>

        <div className="flex-1 overflow-y-auto px-5 py-4">
          <dl>
            <Row term="Endpoint">{evidence.source_endpoint}</Row>
            <Row term="Field path">{evidence.field_path ?? "whole record"}</Row>
            <Row term="Point date">{evidence.point_date ?? "undated"}</Row>
            <Row term="Retrieved at">{evidence.retrieved_at}</Row>
            {evidence.url && (
              <Row term="URL">
                <a href={evidence.url} target="_blank" rel="noreferrer" className="btn-link">{evidence.url}</a>
              </Row>
            )}
            <Row term="Cache key">
              {evidence.cache_key ? (
                <span className="flex items-start gap-2">
                  <span className="min-w-0 flex-1">{evidence.cache_key}</span>
                  <CopyButton text={evidence.cache_key} label="Copy cache key" />
                </span>
              ) : "none"}
            </Row>
          </dl>

          <h3 className="mt-5 font-sans text-sm font-semibold text-ink">Verbatim excerpt</h3>
          <pre className="mt-1.5 whitespace-pre-wrap break-words rounded border border-line bg-sunken p-3 font-mono text-sm text-ink">
            {evidence.excerpt}
          </pre>
        </div>
      </div>
    </div>
  );
}
