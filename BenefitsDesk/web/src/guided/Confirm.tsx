import { useEffect, useState } from "react";
import { api, errText, type IntakeItem, type Stage } from "./api";
import { Button, ErrorText, Loading, Tag, line, muted, sourcePanel, type Panel } from "./ui";

type Answer = { action: "confirm" } | { action: "edit"; value: unknown };
const KIND_TAG = { checked: "Checked", guessed: "Our guess", missing: "Not found" } as const;

const show = (v: unknown) => (v == null || v === "" ? "Not found" : typeof v === "object" ? JSON.stringify(v) : String(v));

export default function Confirm({ onDone, openPanel }: { onDone: (stage: Stage, message?: string) => void; openPanel: (p: Panel) => void }) {
  const [items, setItems] = useState<IntakeItem[] | null>(null);
  const [ans, setAns] = useState<Record<string, Answer>>({});
  const [editing, setEditing] = useState<string | null>(null);
  const [draft, setDraft] = useState("");
  const [err, setErr] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    api<{ items: IntakeItem[] }>("/api/intake").then((r) => setItems(r.items || [])).catch((e) => setErr(errText(e)));
  }, []);

  const set = (key: string, a: Answer) => { setAns((x) => ({ ...x, [key]: a })); setEditing(null); setDraft(""); };
  const all = !!items && items.every((i) => ans[i.key]);

  async function submit() {
    setBusy(true); setErr("");
    try {
      const r = await api<{ stage: Stage; message?: string }>("/api/intake", { items: ans });
      onDone(r.stage, r.message);
    } catch (e) { setErr(errText(e)); } finally { setBusy(false); }
  }

  return (
    <div className="mx-auto max-w-2xl py-10">
      <h1 className="text-2xl font-semibold">Is this you?</h1>
      <p className={`mt-2 text-sm ${muted}`}>We found these details in your public work record. Mark each one Correct, or Change it.</p>
      <div className={`mt-8 rounded-lg border ${line}`}>
        {!items && !err && <div className="p-5"><Loading text="Looking up your work record" /></div>}
        {items && items.length === 0 && <p className={`p-5 text-sm ${muted}`}>Nothing to check.</p>}
        <ul className="divide-y divide-neutral-200 dark:divide-neutral-800">
          {items?.map((it) => {
            const a = ans[it.key];
            const missing = it.kind === "missing";
            const open = editing === it.key || (missing && !a);
            const shown = a?.action === "edit" ? a.value : it.value;
            return (
              <li key={it.key} className="p-5">
                <div className="flex flex-wrap items-start gap-x-3 gap-y-1">
                  <div className="min-w-0 flex-1">
                    <div className={`text-sm ${muted}`}>{it.label}</div>
                    <div className="mt-0.5 text-base font-medium">{missing && !a ? (it.question || "We could not find this") : show(shown)}</div>
                  </div>
                  <Tag>{a?.action === "edit" ? "Changed by you" : KIND_TAG[it.kind]}</Tag>
                </div>
                {it.kind === "guessed" && !a && (
                  <p className={`mt-2 text-sm ${muted}`}>
                    {it.key === "age_band" ? "Our guess from your education dates — please check." : "This is our guess — please check."}
                    {it.basis ? ` ${it.basis}` : ""}
                  </p>
                )}
                {missing && it.question && a && <p className={`mt-1 text-sm ${muted}`}>{it.question}</p>}

                {open ? (
                  <div className="mt-3">
                    {it.choices && it.choices.length > 0 ? (
                      <div className="flex flex-wrap gap-2" role="group" aria-label={it.label}>
                        {it.choices.map((c) => (
                          <Button key={c} pressed={a?.action === "edit" && a.value === c} onClick={() => set(it.key, { action: "edit", value: c })}>{c}</Button>
                        ))}
                      </div>
                    ) : (
                      <form className="flex flex-wrap gap-2" onSubmit={(e) => { e.preventDefault(); if (draft.trim()) set(it.key, { action: "edit", value: draft.trim() }); }}>
                        <label htmlFor={`f-${it.key}`} className="sr-only">{it.label}</label>
                        <input id={`f-${it.key}`} autoFocus className={`min-w-0 flex-1 rounded-lg border ${line} bg-transparent px-3 py-2`}
                          value={draft} onChange={(e) => setDraft(e.target.value)} />
                        <Button kind="primary" type="submit" disabled={!draft.trim()}>Save</Button>
                      </form>
                    )}
                    {!missing && <Button kind="quiet" className="mt-2" onClick={() => setEditing(null)}>Cancel</Button>}
                  </div>
                ) : (
                  <div className="mt-3 flex flex-wrap items-center gap-2">
                    {!missing && <Button pressed={a?.action === "confirm"} onClick={() => set(it.key, { action: "confirm" })}>Correct</Button>}
                    <Button pressed={false} onClick={() => { setEditing(it.key); setDraft(typeof shown === "string" ? shown : ""); }}>Change</Button>
                    {it.source && <Button kind="quiet" onClick={() => openPanel(sourcePanel(`Source: ${it.label}`, it.source))}>Source</Button>}
                  </div>
                )}
              </li>
            );
          })}
        </ul>
      </div>
      <div className="mt-6 space-y-3">
        <ErrorText>{err}</ErrorText>
        <div className="flex items-center gap-4">
          <Button kind="primary" disabled={!all || busy} onClick={submit}>{busy ? "Saving…" : "Continue"}</Button>
          {items && !all && <span className={`text-sm ${muted}`}>{items.filter((i) => !ans[i.key]).length} left to answer</span>}
        </div>
      </div>
    </div>
  );
}
