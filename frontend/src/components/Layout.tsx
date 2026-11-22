import { Suspense } from "react";
import { NavLink, Outlet } from "react-router-dom";
import { useHealth } from "../lib/health";
import { BackendDown } from "./BackendDown";
import { ListSkeleton } from "./States";

const NAV = [
  { to: "/", label: "Home", end: true },
  { to: "/files", label: "Files", end: false },
  { to: "/audit", label: "Audit", end: false },
  { to: "/watch", label: "Watch", end: false },
  { to: "/ledger", label: "Ledger", end: false },
];

function ModeBadge() {
  const { state } = useHealth();
  if (state.status === "checking") return <span className="tag">checking…</span>;
  if (state.status === "down") return <span className="chip bg-danger-tint text-danger">API offline</span>;
  const replay = state.health.mode === "replay";
  return (
    <span className={`chip ${replay ? "bg-sunken text-ink" : "bg-refuse-tint text-refuse"}`}
      title={replay ? "Replay: recorded responses only, 0 credits"
        : "Live: stored copies first; a Crustdata lookup only after you confirm its estimate"}>
      <span className="font-mono">{state.health.mode}</span>
      <span className="ml-1 text-muted">
        · {replay ? "0 credits" : `confirm before spend · ${state.health.session_left_credits} credits left`}
      </span>
    </span>
  );
}

export function Layout() {
  const { state } = useHealth();
  return (
    <div className="flex min-h-screen flex-col">
      <a href="#main" className="sr-only focus:not-sr-only focus:absolute focus:left-4 focus:top-2 focus:z-modal focus:rounded focus:bg-surface focus:px-3 focus:py-2">
        Skip to content
      </a>
      <header className="sticky top-0 z-nav border-b border-line bg-surface">
        <div className="mx-auto flex max-w-5xl flex-wrap items-center gap-x-6 gap-y-2 px-4 py-3 sm:px-6">
          <NavLink to="/" className="font-serif text-xl font-semibold text-ink" aria-label="AsOf home">
            AsOf
          </NavLink>
          <nav aria-label="Main" className="order-3 w-full sm:order-none sm:w-auto">
            <ul className="-mx-2 flex flex-wrap gap-1">
              {NAV.map((n) => (
                <li key={n.to}>
                  <NavLink
                    to={n.to}
                    end={n.end}
                    className={({ isActive }) =>
                      `block rounded px-2.5 py-1.5 text-sm font-medium ${isActive ? "bg-accent-tint text-accent" : "text-muted hover:text-ink"}`}
                  >
                    {n.label}
                  </NavLink>
                </li>
              ))}
            </ul>
          </nav>
          <div className="ml-auto"><ModeBadge /></div>
        </div>
      </header>

      <main id="main" className="mx-auto w-full max-w-5xl flex-1 px-4 py-8 sm:px-6">
        {state.status === "down" ? (
          <BackendDown />
        ) : state.status === "checking" ? (
          <ListSkeleton rows={3} label="Connecting to the AsOf API" />
        ) : (
          <Suspense fallback={<ListSkeleton rows={3} label="Loading page" />}>
            <Outlet />
          </Suspense>
        )}
      </main>

      <footer className="border-t border-line bg-surface">
        <p className="mx-auto max-w-5xl px-4 py-4 text-meta text-muted sm:px-6">
          Every line states what a dated record says and when the stored copy was retrieved, or says
          CANNOT ATTEST and names what is missing. Company records only.
        </p>
      </footer>
    </div>
  );
}
