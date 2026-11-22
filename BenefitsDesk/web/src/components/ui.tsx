import { createContext, useContext, useEffect, useRef, useState, type ReactNode } from "react";
import { AlertTriangle, CheckCircle2, ExternalLink, FileSearch, HelpCircle, Loader2, MessageSquare, ServerOff, X } from "lucide-react";
import { BackendDownError } from "../api";
import type { Fact, Source } from "../types";
import { fmtDate } from "../format";

export function cx(...c: (string | false | null | undefined)[]) {
  return c.filter(Boolean).join(" ");
}

export function Card({ title, icon, actions, children, className, subtitle }: { title?: ReactNode; subtitle?: ReactNode; icon?: ReactNode; actions?: ReactNode; children: ReactNode; className?: string }) {
  return (
    <section className={cx("rounded-2xl border border-slate-200 bg-white shadow-sm dark:border-slate-800 dark:bg-slate-900", className)}>
      {(title || actions) && (
        <header className="flex flex-wrap items-start justify-between gap-3 border-b border-slate-100 px-5 py-4 dark:border-slate-800">
          <div className="min-w-0">
            <h2 className="flex items-center gap-2 text-lg font-semibold text-slate-900 dark:text-slate-50">
              {icon}
              {title}
            </h2>
            {subtitle && <p className="mt-0.5 text-sm text-slate-600 dark:text-slate-400">{subtitle}</p>}
          </div>
          {actions && <div className="flex flex-wrap items-center gap-2">{actions}</div>}
        </header>
      )}
      <div className="p-5">{children}</div>
    </section>
  );
}

export function Badge({ children, tone = "slate", className }: { children: ReactNode; tone?: "slate" | "green" | "amber" | "red" | "blue" | "violet"; className?: string }) {
  const tones: Record<string, string> = {
    slate: "bg-slate-100 text-slate-800 ring-slate-300 dark:bg-slate-800 dark:text-slate-200 dark:ring-slate-600",
    green: "bg-emerald-50 text-emerald-900 ring-emerald-300 dark:bg-emerald-950 dark:text-emerald-200 dark:ring-emerald-800",
    amber: "bg-amber-50 text-amber-900 ring-amber-300 dark:bg-amber-950 dark:text-amber-200 dark:ring-amber-800",
    red: "bg-red-50 text-red-900 ring-red-300 dark:bg-red-950 dark:text-red-200 dark:ring-red-800",
    blue: "bg-sky-50 text-sky-900 ring-sky-300 dark:bg-sky-950 dark:text-sky-200 dark:ring-sky-800",
    violet: "bg-violet-50 text-violet-900 ring-violet-300 dark:bg-violet-950 dark:text-violet-200 dark:ring-violet-800",
  };
  return <span className={cx("inline-flex items-center gap-1 whitespace-nowrap rounded-full px-2.5 py-0.5 text-sm font-medium ring-1 ring-inset", tones[tone], className)}>{children}</span>;
}

export function Button({ children, variant = "secondary", className, ...props }: React.ButtonHTMLAttributes<HTMLButtonElement> & { variant?: "primary" | "secondary" | "danger" | "ghost" }) {
  const v: Record<string, string> = {
    primary: "bg-indigo-600 text-white hover:bg-indigo-700 disabled:bg-indigo-300 dark:disabled:bg-indigo-900 dark:disabled:text-indigo-400",
    secondary: "bg-white text-slate-900 ring-1 ring-inset ring-slate-300 hover:bg-slate-50 disabled:text-slate-400 dark:bg-slate-800 dark:text-slate-100 dark:ring-slate-600 dark:hover:bg-slate-700 dark:disabled:text-slate-500",
    danger: "bg-red-600 text-white hover:bg-red-700 disabled:bg-red-300 dark:disabled:bg-red-950 dark:disabled:text-red-400",
    ghost: "text-slate-700 hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-slate-800",
  };
  return (
    <button {...props} className={cx("inline-flex items-center justify-center gap-2 rounded-lg px-3.5 py-2 text-base font-semibold transition-colors disabled:cursor-not-allowed", v[variant], className)}>
      {children}
    </button>
  );
}

export function Loading({ label = "Loading…" }: { label?: string }) {
  return (
    <div role="status" className="flex items-center gap-2 py-6 text-slate-600 dark:text-slate-400">
      <Loader2 className="h-5 w-5 animate-spin" aria-hidden /> {label}
    </div>
  );
}

export function Empty({ title, children, icon }: { title: string; children?: ReactNode; icon?: ReactNode }) {
  return (
    <div className="flex flex-col items-center justify-center gap-2 rounded-xl border border-dashed border-slate-300 px-6 py-10 text-center dark:border-slate-700">
      <div className="text-slate-400 dark:text-slate-500">{icon ?? <FileSearch className="h-8 w-8" aria-hidden />}</div>
      <p className="font-semibold text-slate-800 dark:text-slate-200">{title}</p>
      {children && <div className="max-w-prose text-slate-600 dark:text-slate-400">{children}</div>}
    </div>
  );
}

export function BackendDown() {
  return (
    <div role="alert" className="flex items-start gap-3 rounded-xl border border-red-300 bg-red-50 p-4 text-red-900 dark:border-red-800 dark:bg-red-950 dark:text-red-100">
      <ServerOff className="mt-0.5 h-5 w-5 shrink-0" aria-hidden />
      <div>
        <p className="font-semibold">Backend not running — start it with <code className="rounded bg-red-100 px-1.5 py-0.5 font-mono text-[0.95em] dark:bg-red-900">uv run bd serve</code></p>
        <p className="text-sm opacity-90">The page will reconnect on its own once the service answers on port 8787.</p>
      </div>
    </div>
  );
}

export function ErrorState({ error, onRetry }: { error: unknown; onRetry?: () => void }) {
  if (error instanceof BackendDownError) return <BackendDown />;
  return (
    <div role="alert" className="flex items-start justify-between gap-3 rounded-xl border border-red-300 bg-red-50 p-4 text-red-900 dark:border-red-800 dark:bg-red-950 dark:text-red-100">
      <div className="flex items-start gap-2">
        <AlertTriangle className="mt-0.5 h-5 w-5 shrink-0" aria-hidden />
        <span>{error instanceof Error ? error.message : String(error)}</span>
      </div>
      {onRetry && (
        <Button variant="secondary" onClick={onRetry}>
          Retry
        </Button>
      )}
    </div>
  );
}

/* ---------------- Fact labels: colour + icon + text ---------------- */
export const LABEL_META: Record<Fact["label"], { text: string; cls: string; dot: string; hint: string }> = {
  told: {
    text: "Told",
    hint: "The person said this",
    cls: "bg-sky-50 text-sky-950 ring-sky-400 dark:bg-sky-950 dark:text-sky-100 dark:ring-sky-600",
    dot: "bg-sky-600 dark:bg-sky-400",
  },
  checked: {
    text: "Checked",
    hint: "Confirmed against a record",
    cls: "bg-emerald-50 text-emerald-950 ring-emerald-400 dark:bg-emerald-950 dark:text-emerald-100 dark:ring-emerald-600",
    dot: "bg-emerald-600 dark:bg-emerald-400",
  },
  guessed: {
    text: "Guessed",
    hint: "Inferred, not confirmed",
    cls: "bg-amber-50 text-amber-950 ring-amber-400 dark:bg-amber-950 dark:text-amber-100 dark:ring-amber-600",
    dot: "bg-amber-500 dark:bg-amber-400",
  },
};

export function LabelIcon({ label, className = "h-4 w-4" }: { label: Fact["label"]; className?: string }) {
  if (label === "told") return <MessageSquare className={className} aria-hidden />;
  if (label === "checked") return <CheckCircle2 className={className} aria-hidden />;
  return <HelpCircle className={className} aria-hidden />;
}

export function LabelTag({ label }: { label: Fact["label"] }) {
  const m = LABEL_META[label] ?? LABEL_META.guessed;
  return (
    <span className={cx("inline-flex items-center gap-1 rounded-md px-1.5 py-0.5 text-xs font-bold uppercase tracking-wide ring-1 ring-inset", m.cls, label === "guessed" && "border border-dashed border-amber-500")}>
      <LabelIcon label={label} className="h-3.5 w-3.5" />
      {m.text}
    </span>
  );
}

/* ---------------- Source drawer (global) ---------------- */
type DrawerContent = { title: string; source?: Source | null; sources?: Source[]; extra?: ReactNode };
const DrawerCtx = createContext<{ open: (c: DrawerContent) => void; close: () => void }>({ open: () => {}, close: () => {} });
export const useDrawer = () => useContext(DrawerCtx);

export function DrawerProvider({ children }: { children: ReactNode }) {
  const [content, setContent] = useState<DrawerContent | null>(null);
  const lastFocus = useRef<HTMLElement | null>(null);
  const panel = useRef<HTMLDivElement>(null);
  const open = (c: DrawerContent) => {
    lastFocus.current = document.activeElement as HTMLElement;
    setContent(c);
  };
  const close = () => {
    setContent(null);
    lastFocus.current?.focus?.();
  };
  useEffect(() => {
    if (!content) return;
    panel.current?.focus();
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") close();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [content]);
  const sources = content ? (content.sources ?? (content.source ? [content.source] : [])) : [];
  return (
    <DrawerCtx.Provider value={{ open, close }}>
      {children}
      {content && (
        <div className="fixed inset-0 z-50 flex justify-end" role="dialog" aria-modal="true" aria-labelledby="drawer-title">
          <button aria-label="Close source panel" className="absolute inset-0 cursor-default bg-slate-950/40 backdrop-blur-[1px]" onClick={close} tabIndex={-1} />
          <div ref={panel} tabIndex={-1} className="relative flex h-full w-full max-w-xl animate-drawer-in flex-col overflow-y-auto border-l border-slate-200 bg-white shadow-2xl outline-none dark:border-slate-800 dark:bg-slate-900">
            <div className="sticky top-0 flex items-start justify-between gap-3 border-b border-slate-200 bg-white/95 px-6 py-4 backdrop-blur dark:border-slate-800 dark:bg-slate-900/95">
              <div>
                <p className="text-sm font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">Where this comes from</p>
                <h3 id="drawer-title" className="text-xl font-semibold text-slate-900 dark:text-slate-50">
                  {content.title}
                </h3>
              </div>
              <Button variant="ghost" onClick={close} aria-label="Close">
                <X className="h-5 w-5" aria-hidden />
              </Button>
            </div>
            <div className="space-y-5 px-6 py-5">
              {content.extra}
              {sources.length === 0 ? (
                <Empty title="No source on record">This item has no source attached. Treat it as unconfirmed.</Empty>
              ) : (
                sources.map((s, i) => <SourceDetail key={i} source={s} index={sources.length > 1 ? i + 1 : undefined} />)
              )}
            </div>
          </div>
        </div>
      )}
    </DrawerCtx.Provider>
  );
}

export function SourceDetail({ source, index }: { source: Source; index?: number }) {
  const row = (k: string, v: ReactNode) => (
    <div className="grid grid-cols-[8.5rem_1fr] gap-3 border-b border-slate-100 py-2 last:border-0 dark:border-slate-800">
      <dt className="text-sm font-medium text-slate-500 dark:text-slate-400">{k}</dt>
      <dd className="min-w-0 break-words text-slate-900 dark:text-slate-100">{v}</dd>
    </div>
  );
  return (
    <div className="rounded-xl border border-slate-200 p-4 dark:border-slate-700">
      {index && <p className="mb-2 text-sm font-semibold text-slate-500">Source {index}</p>}
      <dl>
        {row("Record", <span className="font-mono text-[0.92em]">{source.record}</span>)}
        {source.record_id && row("Record id", <span className="font-mono text-[0.92em]">{source.record_id}</span>)}
        {row("Field path", source.field_path ? <span className="font-mono text-[0.92em]">{source.field_path}</span> : "—")}
        {row("Record date", fmtDate(source.record_date))}
        {row("Retrieved", fmtDate(source.retrieved_at))}
        {row(
          "Link",
          source.url ? (
            <a href={source.url} target="_blank" rel="noreferrer noopener" className="inline-flex items-center gap-1 break-all text-indigo-700 underline underline-offset-2 hover:text-indigo-900 dark:text-indigo-300 dark:hover:text-indigo-200">
              {source.url} <ExternalLink className="h-4 w-4 shrink-0" aria-hidden />
            </a>
          ) : (
            "—"
          ),
        )}
      </dl>
      {source.passage && (
        <blockquote className="mt-3 border-l-4 border-indigo-400 bg-indigo-50/60 px-4 py-3 text-slate-800 dark:border-indigo-500 dark:bg-indigo-950/40 dark:text-slate-200">
          “{source.passage}”
        </blockquote>
      )}
    </div>
  );
}

export function SourceButton({ source, sources, title, children, className }: { source?: Source | null; sources?: Source[]; title: string; children?: ReactNode; className?: string }) {
  const { open } = useDrawer();
  return (
    <button type="button" onClick={() => open({ title, source, sources })} className={cx("inline-flex items-center gap-1 text-sm font-medium text-indigo-700 underline decoration-dotted underline-offset-4 hover:text-indigo-900 dark:text-indigo-300 dark:hover:text-indigo-100", className)}>
      <FileSearch className="h-4 w-4" aria-hidden />
      {children ?? "Source"}
    </button>
  );
}

export function JsonBlock({ value, summary = "Show JSON" }: { value: unknown; summary?: string }) {
  return (
    <details className="group rounded-lg border border-slate-200 dark:border-slate-700">
      <summary className="cursor-pointer select-none px-3 py-2 text-sm font-semibold text-slate-700 dark:text-slate-300">{summary}</summary>
      <pre className="max-h-80 overflow-auto border-t border-slate-200 bg-slate-50 p-3 font-mono text-sm text-slate-800 dark:border-slate-700 dark:bg-slate-950 dark:text-slate-200">{JSON.stringify(value, null, 2)}</pre>
    </details>
  );
}

export function Stat({ label, value, hint }: { label: string; value: ReactNode; hint?: ReactNode }) {
  return (
    <div className="rounded-xl border border-slate-200 px-4 py-3 dark:border-slate-800">
      <p className="text-sm text-slate-600 dark:text-slate-400">{label}</p>
      <p className="text-2xl font-semibold tabular-nums text-slate-900 dark:text-slate-50">{value}</p>
      {hint && <p className="text-sm text-slate-500 dark:text-slate-400">{hint}</p>}
    </div>
  );
}
