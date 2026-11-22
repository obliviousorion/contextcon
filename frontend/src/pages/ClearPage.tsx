import { Link, useParams } from "react-router-dom";
import { CaseFileLoader } from "../components/CaseFileLoader";
import { useHealth } from "../lib/health";

export default function ClearPage() {
  const { domain = "" } = useParams();
  const { today } = useHealth();
  return (
    <>
      <nav aria-label="File views" className="mx-auto mb-4 flex max-w-file flex-wrap gap-x-4 text-sm">
        <span className="font-medium text-ink">Clearance (today)</span>
        <Link className="btn-link" to={`/dispute/${encodeURIComponent(domain)}?as_of=${today}`}>
          Dispute file: move the date
        </Link>
      </nav>
      <CaseFileLoader tool="clear" domain={domain} />
    </>
  );
}
