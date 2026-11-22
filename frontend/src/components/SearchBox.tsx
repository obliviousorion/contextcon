import { useState, type FormEvent } from "react";
import { useNavigate } from "react-router-dom";
import { looksLikeDomain, normalizeDomainInput } from "../lib/format";

/** Target of a search: a domain is cleared directly; a name is resolved (never auto-picked). */
export function searchTarget(raw: string): string | null {
  const t = raw.trim();
  if (!t) return null;
  if (looksLikeDomain(t)) return `/clear/${encodeURIComponent(normalizeDomainInput(t))}`;
  return `/resolve?q=${encodeURIComponent(t)}`;
}

export function SearchBox({ initial = "", autoFocus = false }: { initial?: string; autoFocus?: boolean }) {
  const [q, setQ] = useState(initial);
  const navigate = useNavigate();

  const submit = (e: FormEvent) => {
    e.preventDefault();
    const to = searchTarget(q);
    if (to) navigate(to);
  };

  return (
    <form onSubmit={submit} role="search" className="flex flex-col gap-2 sm:flex-row">
      <label htmlFor="q" className="sr-only">Company domain or name</label>
      <input
        id="q"
        className="input py-2.5 text-base"
        placeholder="delhivery.com or a company name"
        value={q}
        onChange={(e) => setQ(e.target.value)}
        autoFocus={autoFocus}
        autoComplete="off"
        spellCheck={false}
        aria-describedby="q-hint"
      />
      <button type="submit" className="btn-primary px-5" disabled={!q.trim()}>Check</button>
      <span id="q-hint" className="sr-only">A domain opens a clearance file. A name lists candidates to choose from.</span>
    </form>
  );
}
