// Small, plain building blocks for the guided UI. One accent (#2563eb = blue-600), greys for the rest.
import { forwardRef, useEffect, useRef } from "react";
import type { Label, Source } from "./api";
import { SourceRows } from "./Graph";

export const line = "border-neutral-200 dark:border-neutral-800";
export const muted = "text-neutral-500 dark:text-neutral-400";

type BtnProps = React.ButtonHTMLAttributes<HTMLButtonElement> & { kind?: "primary" | "plain" | "quiet"; pressed?: boolean };
export const Button = forwardRef<HTMLButtonElement, BtnProps>(function Button({ kind = "plain", pressed, className = "", ...p }, ref) {
  const base = "inline-flex items-center justify-center rounded-lg px-4 py-2 text-sm font-medium disabled:cursor-not-allowed disabled:opacity-50";
  const look = kind === "primary"
    ? "bg-blue-600 text-white hover:bg-blue-700"
    : kind === "quiet"
      ? "text-neutral-600 hover:text-neutral-900 underline-offset-4 hover:underline dark:text-neutral-300 dark:hover:text-white px-2"
      : pressed
        ? "border border-blue-600 bg-blue-600 text-white"
        : `border ${line} bg-transparent hover:bg-neutral-50 dark:hover:bg-neutral-900`;
  return <button ref={ref} type="button" aria-pressed={pressed} className={`${base} ${look} ${className}`} {...p} />;
});

const LABEL_TEXT: Record<Label, string> = { told: "Told", checked: "Checked", guessed: "Guessed" };
export function Tag({ children }: { children: React.ReactNode }) {
  return <span className="inline-block shrink-0 rounded border border-neutral-300 px-1.5 py-px text-xs text-neutral-600 dark:border-neutral-700 dark:text-neutral-300">{children}</span>;
}
export const LabelTag = ({ label }: { label: Label }) => <Tag>{LABEL_TEXT[label] ?? label}</Tag>;

export function CannotVerify({ missing }: { missing?: string }) {
  return <span className="text-sm text-neutral-700 dark:text-neutral-300"><span className="font-medium">Cannot verify</span>{missing ? `: ${missing}` : ""}</span>;
}

export function Tile({ title, className = "", children, aside }: { title: string; className?: string; children: React.ReactNode; aside?: React.ReactNode }) {
  const id = `t-${title.toLowerCase().replace(/[^a-z]+/g, "-")}`;
  return (
    <section aria-labelledby={id} className={`min-w-0 rounded-lg border ${line} p-5 ${className}`}>
      <div className="mb-4 flex items-baseline gap-3">
        <h2 id={id} className="mr-auto text-base font-semibold">{title}</h2>
        {aside}
      </div>
      {children}
    </section>
  );
}

export function Loading({ text = "Loading" }: { text?: string }) {
  return <p role="status" className={`text-sm ${muted}`}>{text}…</p>;
}
export function Empty({ children }: { children: React.ReactNode }) {
  return <p className={`text-sm ${muted}`}>{children}</p>;
}
export function ErrorText({ children }: { children: React.ReactNode }) {
  if (!children) return null;
  return <p role="alert" className="rounded-lg border border-neutral-300 p-3 text-sm text-neutral-900 dark:border-neutral-700 dark:text-neutral-100"><span className="font-medium">Problem: </span>{children}</p>;
}

export const day = (s?: string | null) => (s ? String(s).slice(0, 10) : "");

export type Panel = { title: string; body: React.ReactNode } | null;

/** Right-hand panel for sources and graph node cards. */
export function SidePanel({ panel, onClose }: { panel: Panel; onClose: () => void }) {
  const closeRef = useRef<HTMLButtonElement>(null);
  useEffect(() => {
    if (!panel) return;
    const prev = document.activeElement as HTMLElement | null;
    closeRef.current?.focus();
    const k = (e: KeyboardEvent) => { if (e.key === "Escape") onClose(); };
    window.addEventListener("keydown", k);
    return () => { window.removeEventListener("keydown", k); prev?.focus?.(); };
  }, [panel, onClose]);
  if (!panel) return null;
  return (
    <div className="fixed inset-0 z-40 flex justify-end bg-black/30" onClick={onClose}>
      <div role="dialog" aria-modal="true" aria-labelledby="panel-title"
        className={`h-full w-full max-w-md overflow-auto border-l ${line} bg-white p-6 dark:bg-[#0a0a0a]`} onClick={(e) => e.stopPropagation()}>
        <div className="mb-4 flex items-start gap-3">
          <h3 id="panel-title" className="mr-auto text-base font-semibold">{panel.title}</h3>
          <Button ref={closeRef} onClick={onClose}>Close</Button>
        </div>
        {panel.body}
      </div>
    </div>
  );
}

export function sourcePanel(title: string, s: Source | null | undefined, extra?: React.ReactNode): Panel {
  return { title, body: <div className="space-y-4">{extra}<SourceRows s={s} /></div> };
}

export function Confirm({ text, yes, onYes, onNo }: { text: string; yes: string; onYes: () => void; onNo: () => void }) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30 p-4" onClick={onNo}>
      <div role="alertdialog" aria-modal="true" aria-labelledby="confirm-text"
        className={`w-full max-w-sm rounded-lg border ${line} bg-white p-6 dark:bg-[#0a0a0a]`} onClick={(e) => e.stopPropagation()}>
        <p id="confirm-text" className="mb-5 text-sm">{text}</p>
        <div className="flex justify-end gap-2">
          <Button autoFocus onClick={onNo}>Cancel</Button>
          <Button kind="primary" onClick={onYes}>{yes}</Button>
        </div>
      </div>
    </div>
  );
}
