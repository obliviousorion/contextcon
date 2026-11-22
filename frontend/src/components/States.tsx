import type { ReactNode } from "react";

export function Skeleton({ className = "" }: { className?: string }) {
  return <div className={`skeleton ${className}`} aria-hidden="true" />;
}

/** Static placeholder rows (no pulse) while a case file or list loads. */
export function ListSkeleton({ rows = 5, label = "Loading" }: { rows?: number; label?: string }) {
  return (
    <div role="status" aria-live="polite" className="surface divide-y divide-line">
      <span className="sr-only">{label}…</span>
      {Array.from({ length: rows }, (_, i) => (
        <div key={i} className="flex gap-4 p-4">
          <Skeleton className="h-4 w-24 shrink-0" />
          <div className="flex-1 space-y-2">
            <Skeleton className="h-4 w-1/3" />
            <Skeleton className="h-4 w-full" />
          </div>
        </div>
      ))}
    </div>
  );
}

export function ErrorState({ message, onRetry, title = "The request failed" }:
  { message: string; onRetry?: () => void; title?: string }) {
  return (
    <div role="alert" className="rounded-lg border border-danger bg-danger-tint p-5">
      <h2 className="text-lg text-danger">{title}</h2>
      <p className="mt-1 break-words text-ink">
        <span className="text-muted">Server message: </span>
        <span className="font-mono text-sm">{message}</span>
      </p>
      {onRetry && (
        <button type="button" onClick={onRetry} className="btn-secondary mt-3">Retry</button>
      )}
    </div>
  );
}

export function EmptyState({ title, children }: { title: string; children?: ReactNode }) {
  return (
    <div className="surface p-8 text-center">
      <h2 className="text-lg">{title}</h2>
      {children && <div className="mx-auto mt-1 max-w-md text-muted">{children}</div>}
    </div>
  );
}

export function PageTitle({ title, children }: { title: string; children?: ReactNode }) {
  return (
    <div className="mb-6">
      <h1 className="text-[28px] leading-tight text-ink">{title}</h1>
      {children && <p className="mt-1.5 max-w-2xl text-muted">{children}</p>}
    </div>
  );
}
