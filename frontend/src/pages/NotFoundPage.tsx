import { Link } from "react-router-dom";
import { EmptyState } from "../components/States";

export default function NotFoundPage() {
  return (
    <div className="mx-auto max-w-file">
      <EmptyState title="No page at this address">
        <Link to="/" className="btn-link">Go to Home</Link> to start from a domain.
      </EmptyState>
    </div>
  );
}
