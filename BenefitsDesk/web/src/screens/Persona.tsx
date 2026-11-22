import { useMemo, useState } from "react";
import { AlertTriangle, BadgeCheck, Check, Pencil, UserRound } from "lucide-react";
import { api } from "../api";
import type { CaseFile, Fact } from "../types";
import { fmtValue } from "../format";
import { Badge, Button, Card, Empty, ErrorState, LABEL_META, LabelIcon, LabelTag, cx, useDrawer } from "../components/ui";

export function PersonaScreen({ c, onChanged }: { c: CaseFile; onChanged: () => void }) {
  const facts = c.facts ?? [];
  const { open } = useDrawer();
  const counts = useMemo(() => {
    const m = { told: 0, checked: 0, guessed: 0 } as Record<Fact["label"], number>;
    facts.forEach((f) => (m[f.label] = (m[f.label] ?? 0) + 1));
    return m;
  }, [facts]);

  const openFact = (f: Fact) =>
    open({
      title: f.statement,
      source: f.source,
      extra: <FactDetail fact={f} c={c} onChanged={onChanged} />,
    });

  return (
    <>
      <Card title="Persona" icon={<UserRound className="h-5 w-5 text-indigo-600 dark:text-indigo-400" aria-hidden />} subtitle="Built from five answers plus records. Every fact says how we know it.">
        {c.persona ? (
          <div className="flex flex-wrap gap-3">
            <Badge tone="slate">
              Persona <span className="font-mono">{c.persona.persona_id}</span>
            </Badge>
            <Badge tone={c.persona.consent ? "green" : "red"}>{c.persona.consent ? "Opted in · consent on file" : "No consent on file"}</Badge>
            <Badge tone="slate">Sign-ups: {c.persona.signups}</Badge>
          </div>
        ) : (
          <p className="text-slate-600 dark:text-slate-400">This case file has no persona (employer-side request).</p>
        )}
        <div className="mt-4 grid gap-3 sm:grid-cols-3" aria-label="Legend">
          {(Object.keys(LABEL_META) as Fact["label"][]).map((l) => (
            <div key={l} className={cx("flex items-center gap-3 rounded-xl px-3 py-2 ring-1 ring-inset", LABEL_META[l].cls, l === "guessed" && "border border-dashed border-amber-500")}>
              <LabelIcon label={l} className="h-6 w-6" />
              <div>
                <p className="font-bold">
                  {LABEL_META[l].text} <span className="font-normal tabular-nums">· {counts[l] ?? 0}</span>
                </p>
                <p className="text-sm opacity-90">{LABEL_META[l].hint}</p>
              </div>
            </div>
          ))}
        </div>
      </Card>

      <Card title="Fact file" subtitle="Select a fact to see its source, resolve a conflict, or correct it.">
        {facts.length === 0 ? (
          <Empty title="No facts in this case file" />
        ) : (
          <ul className="flex flex-wrap gap-2.5">
            {facts.map((f) => (
              <li key={f.fact_id}>
                <FactChip fact={f} onClick={() => openFact(f)} />
              </li>
            ))}
          </ul>
        )}
      </Card>
    </>
  );
}

export function FactChip({ fact, onClick, compact }: { fact: Fact; onClick: () => void; compact?: boolean }) {
  const m = LABEL_META[fact.label] ?? LABEL_META.guessed;
  return (
    <button
      type="button"
      onClick={onClick}
      className={cx(
        "group flex max-w-full items-start gap-2 rounded-xl px-3 text-left ring-1 ring-inset transition hover:shadow-md",
        compact ? "py-1" : "py-2",
        m.cls,
        fact.label === "guessed" && "border border-dashed border-amber-500",
        fact.conflict && "ring-2 ring-red-500 dark:ring-red-500",
      )}
      aria-label={`${m.text}: ${fact.statement}${fact.conflict ? " (conflict)" : ""}. Open source.`}
    >
      <span className="mt-0.5 flex shrink-0 items-center gap-1 text-xs font-bold uppercase tracking-wide">
        <LabelIcon label={fact.label} className="h-4 w-4" />
        {m.text}
      </span>
      <span className="min-w-0">
        <span className={cx("block font-medium", compact && "text-sm")}>{fact.statement}</span>
        {!compact && (
          <span className="block font-mono text-sm opacity-90">
            {fmtValue(fact.value)}
          </span>
        )}
        {fact.conflict && (
          <span className="mt-1 inline-flex items-center gap-1 rounded bg-red-600 px-1.5 py-0.5 text-xs font-bold uppercase text-white">
            <AlertTriangle className="h-3 w-3" aria-hidden /> Conflict
          </span>
        )}
      </span>
    </button>
  );
}

function parseLike(input: string, original: unknown): unknown {
  const t = input.trim();
  if (typeof original === "number") {
    const n = Number(t);
    return t !== "" && !Number.isNaN(n) ? n : t;
  }
  if (typeof original === "boolean") {
    if (/^(true|yes|y)$/i.test(t)) return true;
    if (/^(false|no|n)$/i.test(t)) return false;
    return t;
  }
  if (original !== null && typeof original === "object") {
    try {
      return JSON.parse(t);
    } catch {
      return t;
    }
  }
  return t;
}

function toInput(v: unknown): string {
  if (v === null || v === undefined) return "";
  if (typeof v === "object") return JSON.stringify(v);
  return String(v);
}

function FactDetail({ fact, c, onChanged }: { fact: Fact; c: CaseFile; onChanged: () => void }) {
  const [value, setValue] = useState(toInput(fact.value));
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState<string | null>(null);
  const [error, setError] = useState<unknown>(null);
  const personaId = c.persona?.persona_id;

  const related = (c.questions ?? []).filter((q) => {
    const hay = `${q.question} ${q.why}`.toLowerCase();
    return hay.includes(fact.fact_id.toLowerCase()) || hay.includes(fact.statement.toLowerCase());
  });

  const save = async (v: unknown) => {
    if (!personaId) return;
    setSaving(true);
    setError(null);
    setSaved(null);
    try {
      await api.correctFact(personaId, fact.fact_id, v);
      setSaved(fmtValue(v));
      onChanged();
    } catch (e) {
      setError(e);
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-center gap-2">
        <LabelTag label={fact.label} />
        <span className="font-mono text-sm text-slate-500 dark:text-slate-400">{fact.fact_id}</span>
      </div>
      <div>
        <p className="text-sm font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">Current value</p>
        <p className="font-mono text-lg">{fmtValue(fact.value)}</p>
      </div>

      {fact.conflict && (
        <div className="rounded-xl border-2 border-red-400 p-4 dark:border-red-700">
          <p className="mb-3 flex items-center gap-2 font-semibold text-red-800 dark:text-red-200">
            <AlertTriangle className="h-5 w-5" aria-hidden /> The person’s answer and the record disagree
          </p>
          <div className="grid gap-3 sm:grid-cols-2">
            <div className={cx("rounded-lg p-3 ring-1 ring-inset", LABEL_META.told.cls)}>
              <p className="text-xs font-bold uppercase">Told</p>
              <p className="font-mono text-lg">{fmtValue(fact.conflict.told)}</p>
              {personaId && (
                <Button className="mt-2" onClick={() => save(fact.conflict!.told)} disabled={saving}>
                  <Check className="h-4 w-4" aria-hidden /> This one is right
                </Button>
              )}
            </div>
            <div className={cx("rounded-lg p-3 ring-1 ring-inset", LABEL_META.checked.cls)}>
              <p className="text-xs font-bold uppercase">Checked</p>
              <p className="font-mono text-lg">{fmtValue(fact.conflict.checked)}</p>
              {personaId && (
                <Button className="mt-2" onClick={() => save(fact.conflict!.checked)} disabled={saving}>
                  <Check className="h-4 w-4" aria-hidden /> This one is right
                </Button>
              )}
            </div>
          </div>
          {related.length > 0 ? (
            <div className="mt-3">
              {related.map((q, i) => (
                <p key={i} className="text-slate-800 dark:text-slate-200">
                  <span className="font-semibold">Question: </span>
                  {q.question} <span className="text-sm text-slate-600 dark:text-slate-400">({q.why})</span>
                </p>
              ))}
            </div>
          ) : (
            <p className="mt-3 text-slate-800 dark:text-slate-200">
              <span className="font-semibold">Question for the person: </span>which of these is correct?
            </p>
          )}
        </div>
      )}

      {personaId ? (
        <form
          className="rounded-xl border border-slate-200 p-4 dark:border-slate-700"
          onSubmit={(e) => {
            e.preventDefault();
            save(parseLike(value, fact.value));
          }}
        >
          <label htmlFor={`edit-${fact.fact_id}`} className="mb-1 flex items-center gap-2 font-semibold">
            <Pencil className="h-4 w-4" aria-hidden /> Correct this fact
          </label>
          <p className="mb-2 text-sm text-slate-600 dark:text-slate-400">A correction from the person is stored as a new fact labelled “Told”.</p>
          <div className="flex gap-2">
            <input
              id={`edit-${fact.fact_id}`}
              value={value}
              onChange={(e) => setValue(e.target.value)}
              className="min-w-0 flex-1 rounded-lg border border-slate-300 bg-white px-3 py-2 font-mono dark:border-slate-600 dark:bg-slate-800"
            />
            <Button type="submit" variant="primary" disabled={saving || value.trim() === ""}>
              {saving ? "Saving…" : "Save"}
            </Button>
          </div>
          {saved !== null && (
            <p role="status" className="mt-3 flex items-center gap-2 rounded-lg bg-sky-50 px-3 py-2 text-sky-950 dark:bg-sky-950 dark:text-sky-100">
              <BadgeCheck className="h-5 w-5" aria-hidden /> Saved “{saved}”. This fact is now <LabelTag label="told" />
            </p>
          )}
          {!!error && (
            <div className="mt-3">
              <ErrorState error={error} />
            </div>
          )}
        </form>
      ) : (
        <p className="text-sm text-slate-600 dark:text-slate-400">No persona on this case file, so facts cannot be corrected here.</p>
      )}
    </div>
  );
}
