import { Link } from "react-router-dom";
import { SearchBox, searchTarget } from "../components/SearchBox";

const TRY = ["delhivery.com", "tciexpress.in", "shreebalajigrp.com", "Shree Balaji Logistics", "drl.aero"];

export default function HomePage() {
  return (
    <div className="mx-auto max-w-file pt-6 sm:pt-12">
      <h1 className="text-[34px] leading-tight">AsOf</h1>
      <p className="mt-2 max-w-xl text-[17px] text-ink">
        Give a company domain and get a case file: every line is a dated, cited record or CANNOT ATTEST with
        exactly what is missing.
      </p>

      <div className="surface mt-8 p-5">
        <SearchBox autoFocus />
        <div className="mt-4 flex flex-wrap items-center gap-2">
          <span className="text-meta text-muted">Try</span>
          {TRY.map((t) => (
            <Link key={t} to={searchTarget(t) ?? "/"}
              className={`rounded border border-line bg-sunken px-2 py-0.5 text-sm text-ink hover:border-accent hover:text-accent ${t.includes(" ") ? "" : "font-mono"}`}>
              {t}
            </Link>
          ))}
        </div>
      </div>

      <dl className="mt-8 grid gap-x-8 gap-y-4 text-sm sm:grid-cols-3">
        <div>
          <dt className="font-semibold">Clearance</dt>
          <dd className="text-muted">A domain, as of today. <span className="font-mono">/clear/…</span></dd>
        </div>
        <div>
          <dt className="font-semibold">Dispute</dt>
          <dd className="text-muted">The same file as of a past date D. <Link className="btn-link" to="/dispute/tciexpress.in?as_of=2026-10-15">Example</Link></dd>
        </div>
        <div>
          <dt className="font-semibold">Audit</dt>
          <dd className="text-muted">Check stated claims against the records. <Link className="btn-link" to="/audit">Open</Link></dd>
        </div>
      </dl>
    </div>
  );
}
