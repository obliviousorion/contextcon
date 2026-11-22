import { useState } from "react";
import { api, errText, type Stage } from "./api";
import { Button, ErrorText, line, muted } from "./ui";

const input = `w-full rounded-lg border ${line} bg-transparent px-3 py-2 text-base`;

export default function Login({ onIn, notice }: { onIn: (stage: Stage) => void; notice?: React.ReactNode }) {
  const [byName, setByName] = useState(false);
  const [link, setLink] = useState("");
  const [name, setName] = useState("");
  const [company, setCompany] = useState("");
  const [pin, setPin] = useState("");
  const [consent, setConsent] = useState(false);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");

  const pinOk = /^\d{4}$/.test(pin);
  const whoOk = byName ? name.trim() && company.trim() : link.trim();

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (!whoOk || !pinOk) return;
    setBusy(true); setErr("");
    try {
      const body = byName ? { name: name.trim(), company: company.trim(), pin, consent } : { link: link.trim(), pin, consent };
      const r = await api<{ user_id: string; returning: boolean; stage: Stage }>("/api/login", body);
      onIn(r.stage);
    } catch (x) { setErr(errText(x)); } finally { setBusy(false); }
  }

  return (
    <div className="mx-auto max-w-md py-10">
      <h1 className="text-2xl font-semibold">Sign in</h1>
      <p className={`mt-2 text-sm ${muted}`}>We look up your public work record, you check it, and we show what cover you may be missing. A licensed broker handles any next step, only with your approval.</p>
      {notice && <div className={`mt-6 rounded-lg border ${line} p-4 text-sm`}>{notice}</div>}
      <form onSubmit={submit} className="mt-8 space-y-5" noValidate>
        {!byName ? (
          <div>
            <label htmlFor="link" className="mb-1.5 block text-sm font-medium">LinkedIn link</label>
            <input id="link" className={input} type="url" inputMode="url" autoComplete="url" placeholder="https://www.linkedin.com/in/…"
              value={link} onChange={(e) => setLink(e.target.value)} />
          </div>
        ) : (
          <>
            <div>
              <label htmlFor="name" className="mb-1.5 block text-sm font-medium">Your name</label>
              <input id="name" className={input} autoComplete="name" value={name} onChange={(e) => setName(e.target.value)} />
            </div>
            <div>
              <label htmlFor="company" className="mb-1.5 block text-sm font-medium">Company you work for</label>
              <input id="company" className={input} autoComplete="organization" value={company} onChange={(e) => setCompany(e.target.value)} />
            </div>
          </>
        )}
        <button type="button" className="text-sm text-blue-600 underline underline-offset-4 dark:text-blue-400" onClick={() => setByName(!byName)}>
          {byName ? "Use my LinkedIn link instead" : "Use another profile or just my name and company"}
        </button>
        <div>
          <label htmlFor="pin" className="mb-1.5 block text-sm font-medium">4-digit PIN</label>
          <input id="pin" className={`${input} w-32 tracking-widest`} inputMode="numeric" autoComplete="one-time-code" maxLength={4}
            aria-describedby="pin-help" value={pin} onChange={(e) => setPin(e.target.value.replace(/\D/g, "").slice(0, 4))} />
          <p id="pin-help" className={`mt-1.5 text-xs ${muted}`}>New here? Pick any 4 digits; you will use them to come back.</p>
        </div>
        <label className="flex items-start gap-3 text-sm">
          <input type="checkbox" className="mt-0.5 h-4 w-4 accent-blue-600" checked={consent} onChange={(e) => setConsent(e.target.checked)} />
          <span>This is my own profile and I agree to it being looked up.</span>
        </label>
        <ErrorText>{err}</ErrorText>
        <Button kind="primary" type="submit" className="w-full" disabled={busy || !whoOk || !pinOk}>{busy ? "Signing in…" : "Continue"}</Button>
        <p className={`text-xs ${muted}`}>Demo sign-in, not identity proof.</p>
      </form>
    </div>
  );
}
