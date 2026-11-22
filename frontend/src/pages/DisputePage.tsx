import { Link, useParams, useSearchParams } from "react-router-dom";
import { CaseFileLoader } from "../components/CaseFileLoader";
import { DateControl } from "../components/DateControl";
import { EmptyState } from "../components/States";
import { ISO_DATE } from "../lib/format";
import { useHealth } from "../lib/health";

export default function DisputePage() {
  const { domain = "" } = useParams();
  const [params, setParams] = useSearchParams();
  const { today } = useHealth();
  const asOf = params.get("as_of") ?? "";
  const valid = ISO_DATE.test(asOf);

  // Pushes a history entry, so Back returns to the previous date.
  const move = (d: string) => setParams({ as_of: d });
  const controls = <DateControl key={asOf} domain={domain} value={valid ? asOf : ""} max={today} onChange={move} />;

  return (
    <>
      <nav aria-label="File views" className="mx-auto mb-4 flex max-w-file flex-wrap gap-x-4 text-sm">
        <Link className="btn-link" to={`/clear/${encodeURIComponent(domain)}`}>Clearance (today)</Link>
        <span className="font-medium text-ink">Dispute file as of a past date</span>
      </nav>
      {valid ? (
        <CaseFileLoader tool="dispute" domain={domain} asOf={asOf} controls={controls} />
      ) : (
        <div className="mx-auto max-w-file space-y-5">
          <div className="surface p-5">{controls}</div>
          <EmptyState title="Choose the date D">
            A dispute file states what dated records said on or before D. Pick a date or a preset above.
          </EmptyState>
        </div>
      )}
    </>
  );
}
