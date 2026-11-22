import { useState, type FormEvent } from "react";
import { ISO_DATE } from "../lib/format";

const PRESETS: Record<string, string[]> = {
  "tciexpress.in": ["2020-01-01", "2026-09-01", "2026-10-15"],
  "delhivery.com": ["2022-06-01", "2024-01-01", "2026-10-15"],
};
const DEFAULT_PRESETS = ["2020-01-01", "2022-06-01", "2026-09-01", "2026-10-15"];

interface Props {
  domain: string;
  value: string;
  max: string;
  onChange: (d: string) => void;
}

/** "Move the date": a date input plus presets. Changing it updates the URL, which refetches. */
export function DateControl({ domain, value, max, onChange }: Props) {
  const [draft, setDraft] = useState(value);
  const presets = PRESETS[domain] ?? DEFAULT_PRESETS;
  const valid = ISO_DATE.test(draft);

  const submit = (e: FormEvent) => {
    e.preventDefault();
    if (valid) onChange(draft);
  };

  return (
    <form onSubmit={submit} aria-label="Move the date">
      <div className="flex flex-wrap items-end gap-3">
        <div>
          <label htmlFor="as-of" className="label">As of date D</label>
          <input id="as-of" type="date" className="input w-auto font-mono" value={draft} max={max}
            onChange={(e) => setDraft(e.target.value)} required />
        </div>
        <button type="submit" className="btn-primary" disabled={!valid || draft === value}>Move the date</button>
      </div>
      <div className="mt-3 flex flex-wrap items-center gap-2">
        <span className="text-meta text-muted">Presets</span>
        {presets.map((p) => (
          <button key={p} type="button" aria-pressed={p === value}
            onClick={() => { setDraft(p); onChange(p); }}
            className={`rounded border px-2 py-0.5 font-mono text-sm ${p === value ? "border-accent bg-accent-tint text-accent" : "border-line bg-sunken text-ink hover:border-accent"}`}>
            {p}
          </button>
        ))}
        <button type="button" aria-pressed={max === value} onClick={() => { setDraft(max); onChange(max); }}
          className={`rounded border px-2 py-0.5 text-sm ${max === value ? "border-accent bg-accent-tint text-accent" : "border-line bg-sunken text-ink hover:border-accent"}`}>
          today (<span className="font-mono">{max}</span>)
        </button>
      </div>
    </form>
  );
}
