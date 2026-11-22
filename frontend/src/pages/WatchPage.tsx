import { useState, type FormEvent } from "react";
import { api, errorMessage } from "../lib/api";
import { normalizeDomainInput } from "../lib/format";
import type { WatchResponse } from "../types";
import { ApprovalStepper } from "../components/ApprovalStepper";
import { ErrorState, PageTitle } from "../components/States";
import { WatchTestPanel } from "../components/WatchTestPanel";

type Held = Extract<WatchResponse, { key: string }>;

export default function WatchPage() {
  const [domain, setDomain] = useState("tciexpress.in");
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [watch, setWatch] = useState<Held | null>(null);
  const [refusal, setRefusal] = useState<string | null>(null);
  const [created, setCreated] = useState(false);

  const create = async (e: FormEvent) => {
    e.preventDefault();
    if (pending) return;
    setPending(true);
    setError(null);
    setRefusal(null);
    setWatch(null);
    setCreated(false);
    try {
      const r = await api.watch(normalizeDomainInput(domain));
      if (r.status === "cannot_resolve") setRefusal(r.missing ?? "a domain that matches exactly one company");
      else {
        setWatch(r);
        setCreated(r.status === "created");
      }
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setPending(false);
    }
  };

  return (
    <div className="mx-auto max-w-file space-y-5">
      <PageTitle title="Watch a company">
        A watcher re-attests a company when its record changes and marks stored case-file lines STALE. A real
        alert costs 5 credits; the test alert here is free.
      </PageTitle>

      <form onSubmit={create} className="surface flex flex-col gap-3 p-5 sm:flex-row sm:items-end">
        <div className="flex-1">
          <label htmlFor="watch-domain" className="label">Company domain</label>
          <input id="watch-domain" className="input font-mono" value={domain} required disabled={pending}
            onChange={(e) => setDomain(e.target.value)} />
        </div>
        <button type="submit" className="btn-primary" disabled={pending || !domain.trim()}>
          {pending ? "Requesting…" : "Request a watcher"}
        </button>
      </form>

      <div aria-live="polite" className="space-y-5">
        {error && <ErrorState message={error} title="Could not request the watcher" />}
        {refusal && (
          <div className="surface p-5">
            <h2 className="text-lg">Cannot resolve the company</h2>
            <p className="mt-1"><span className="font-semibold">What would settle it: </span>{refusal}</p>
          </div>
        )}
        {watch && (
          <section className="surface p-5" aria-labelledby="watch-head">
            <h2 id="watch-head" className="text-lg">Watcher on {watch.domain}</h2>
            <dl className="mt-2 grid gap-x-6 gap-y-1 text-sm sm:grid-cols-[auto_1fr]">
              <dt className="text-muted">Key</dt><dd className="break-all font-mono">{watch.key}</dd>
              <dt className="text-muted">Field</dt><dd className="font-mono">{watch.field}</dd>
              <dt className="text-muted">Company id</dt><dd className="font-mono">{watch.company_id}</dd>
            </dl>
            <ApprovalStepper key={watch.key} id={watch.key} status={created ? "issued_sandbox" : "draft"}
              noun="watcher" compact onPhase={(p) => p === "issued" && setCreated(true)} />
          </section>
        )}
        {watch && created && <WatchTestPanel id={watch.key} />}
      </div>
    </div>
  );
}
