import type { CaseFile } from "../types";
import { costNote, fmtDate, fmtDateTime } from "../lib/format";
import { KindBadge } from "./Badges";
import { CopyButton } from "./CopyButton";

export function CaseFileHeader({ cf }: { cf: CaseFile }) {
  const entity = cf.attestation?.entity ?? cf.resolve.entity;
  const domain = cf.request.domain ?? entity?.domains[0] ?? "";
  const asOf = cf.attestation?.as_of ?? cf.request.as_of ?? "";
  const lines = cf.attestation?.lines ?? [];
  const attested = lines.filter((l) => l.status === "attested").length;

  return (
    <header className="border-b border-line p-5">
      <div className="flex flex-wrap items-center gap-2">
        <KindBadge kind={cf.kind} />
        <span className="font-mono text-meta text-muted">{cf.id}</span>
        <CopyButton text={cf.id} label={`Copy file id ${cf.id}`} />
      </div>
      <h1 className="mt-2 text-[28px] leading-tight">{entity?.name ?? domain}</h1>
      <p className="break-all font-mono text-sm text-muted">
        {domain}
        {entity && <> · Crustdata id {entity.crustdata_company_id}</>}
      </p>

      <dl className="mt-4 grid gap-x-6 gap-y-2 text-sm sm:grid-cols-[auto_1fr]">
        <dt className="text-muted">As of (D)</dt>
        <dd>
          <time dateTime={asOf} className="font-mono">{asOf}</time>
          <span className="text-muted"> · {fmtDate(asOf)}</span>
        </dd>
        {cf.attestation && (
          <>
            <dt className="text-muted">Lines</dt>
            <dd>{attested} of {lines.length} attested; the rest name what is missing</dd>
            <dt className="text-muted">Generated</dt>
            <dd>{fmtDateTime(cf.attestation.generated_at)}</dd>
          </>
        )}
        <dt className="text-muted">Cost</dt>
        <dd className="text-ink">{costNote(cf.cost)}</dd>
      </dl>
    </header>
  );
}
