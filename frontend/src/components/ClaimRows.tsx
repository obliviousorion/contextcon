import { FIELD_NAMES } from "../types";

export interface ClaimDraft {
  key: number;
  field: string;
  value: string;
  as_of: string;
  text: string;
}

interface Props {
  rows: ClaimDraft[];
  onChange: (rows: ClaimDraft[]) => void;
  disabled?: boolean;
}

const FIELD_SUGGESTIONS = [...FIELD_NAMES, "headcount_growth"];

/** Rows of structured claims: field / value / as_of / text. */
export function ClaimRows({ rows, onChange, disabled }: Props) {
  const set = (key: number, patch: Partial<ClaimDraft>) =>
    onChange(rows.map((r) => (r.key === key ? { ...r, ...patch } : r)));

  return (
    <fieldset disabled={disabled}>
      <legend className="font-sans text-sm font-semibold">Claims</legend>
      <datalist id="claim-fields">
        {FIELD_SUGGESTIONS.map((f) => <option key={f} value={f} />)}
      </datalist>
      <ol className="mt-2 divide-y divide-line border-y border-line">
        {rows.map((r, i) => (
          <li key={r.key} className="grid gap-3 py-4 sm:grid-cols-[1fr_1fr_1fr_auto] sm:items-end">
            <div>
              <label className="label" htmlFor={`f-${r.key}`}>Claim c{i + 1}: field</label>
              <input id={`f-${r.key}`} list="claim-fields" className="input font-mono" value={r.field} required
                onChange={(e) => set(r.key, { field: e.target.value })} />
            </div>
            <div>
              <label className="label" htmlFor={`v-${r.key}`}>Value</label>
              <input id={`v-${r.key}`} className="input font-mono" value={r.value}
                onChange={(e) => set(r.key, { value: e.target.value })} />
            </div>
            <div>
              <label className="label" htmlFor={`d-${r.key}`}>As of</label>
              <input id={`d-${r.key}`} type="date" className="input font-mono" value={r.as_of}
                onChange={(e) => set(r.key, { as_of: e.target.value })} />
            </div>
            <button type="button" className="btn-secondary" disabled={rows.length === 1}
              onClick={() => onChange(rows.filter((x) => x.key !== r.key))}
              aria-label={`Remove claim c${i + 1}`}>
              Remove
            </button>
            <div className="sm:col-span-4">
              <label className="label" htmlFor={`t-${r.key}`}>Claim as stated</label>
              <input id={`t-${r.key}`} className="input" value={r.text} required
                onChange={(e) => set(r.key, { text: e.target.value })} />
            </div>
          </li>
        ))}
      </ol>
    </fieldset>
  );
}
