import { useEffect, useState, type ReactNode } from "react";
import { Building2, ClipboardCheck, Moon, Receipt, Sun, Terminal, UserRound, Users, RefreshCw } from "lucide-react";
import { api, isCaseFile, onBackendStatus } from "./api";
import { useAsync, useInterval } from "./hooks";
import type { CaseFile } from "./types";
import { BackendDown, Button, DrawerProvider, Empty, ErrorState, Loading, cx } from "./components/ui";
import { CaseAside, CaseHeader } from "./components/CaseAside";
import { RunConsole } from "./screens/RunConsole";
import { PersonaScreen } from "./screens/Persona";
import { WorkplaceScreen } from "./screens/Workplace";
import { GapsScreen } from "./screens/Gaps";
import { ApprovalsScreen } from "./screens/Approvals";
import { EmployerScreen } from "./screens/Employer";
import { fmtDate } from "./format";

export type Tab = "console" | "persona" | "workplace" | "gaps" | "approvals" | "employer";

const TABS: { id: Tab; label: string; icon: ReactNode; caseView: boolean }[] = [
  { id: "console", label: "Run console", icon: <Terminal className="h-5 w-5" aria-hidden />, caseView: false },
  { id: "persona", label: "Persona", icon: <UserRound className="h-5 w-5" aria-hidden />, caseView: true },
  { id: "workplace", label: "Workplace", icon: <Users className="h-5 w-5" aria-hidden />, caseView: true },
  { id: "gaps", label: "Gaps & shortlist", icon: <Receipt className="h-5 w-5" aria-hidden />, caseView: true },
  { id: "approvals", label: "Approvals", icon: <ClipboardCheck className="h-5 w-5" aria-hidden />, caseView: true },
  { id: "employer", label: "Employer view", icon: <Building2 className="h-5 w-5" aria-hidden />, caseView: true },
];

function readHash(): { tab: Tab; run: string | null } {
  const [t, r] = window.location.hash.replace(/^#\/?/, "").split("/");
  const tab = (TABS.find((x) => x.id === t)?.id ?? "console") as Tab;
  return { tab, run: r ? decodeURIComponent(r) : null };
}

function useTheme() {
  const [dark, setDark] = useState(() => document.documentElement.classList.contains("dark"));
  useEffect(() => {
    document.documentElement.classList.toggle("dark", dark);
  }, [dark]);
  useEffect(() => {
    const mq = window.matchMedia("(prefers-color-scheme: dark)");
    const on = (e: MediaQueryListEvent) => {
      let saved: string | null = null;
      try {
        saved = localStorage.getItem("bd-theme");
      } catch {
        /* ignore */
      }
      if (!saved) setDark(e.matches);
    };
    mq.addEventListener("change", on);
    return () => mq.removeEventListener("change", on);
  }, []);
  const toggle = () =>
    setDark((d) => {
      try {
        localStorage.setItem("bd-theme", d ? "light" : "dark");
      } catch {
        /* ignore */
      }
      return !d;
    });
  return { dark, toggle };
}

export default function App() {
  const initial = readHash();
  const [tab, setTab] = useState<Tab>(initial.tab);
  const [caseRun, setCaseRun] = useState<string | null>(initial.run);
  const [down, setDown] = useState(false);
  const { dark, toggle } = useTheme();

  useEffect(() => onBackendStatus(setDown), []);

  useEffect(() => {
    const h = `#/${tab}${caseRun && tab !== "console" ? `/${encodeURIComponent(caseRun)}` : ""}`;
    if (window.location.hash !== h) window.history.replaceState(null, "", h);
  }, [tab, caseRun]);

  useEffect(() => {
    const on = () => {
      const h = readHash();
      setTab(h.tab);
      if (h.run) setCaseRun(h.run);
    };
    window.addEventListener("hashchange", on);
    return () => window.removeEventListener("hashchange", on);
  }, []);

  const runs = useAsync(() => api.runs(), []);
  useInterval(() => runs.reload(true), down ? 3000 : 5000);

  // default the case picker to the newest finished run
  useEffect(() => {
    if (!caseRun && runs.data) {
      const fin = runs.data.find((r) => r.status !== "running");
      if (fin) setCaseRun(fin.run_id);
    }
  }, [runs.data, caseRun]);

  const caseQ = useAsync(() => api.caseFile(caseRun!), [caseRun], { enabled: !!caseRun });

  // when the backend comes back, refresh what is on screen
  useEffect(() => {
    if (!down && caseRun && caseQ.error) caseQ.reload();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [down]);

  const openCase = (id: string, t: Tab) => {
    setCaseRun(id);
    setTab(t);
    if (id === caseRun) caseQ.reload();
    window.scrollTo({ top: 0 });
  };

  const current = TABS.find((t) => t.id === tab)!;

  return (
    <DrawerProvider>
      <a href="#main" className="sr-only focus:not-sr-only focus:fixed focus:left-4 focus:top-4 focus:z-50 focus:rounded-lg focus:bg-white focus:px-4 focus:py-2 focus:text-slate-900">
        Skip to content
      </a>
      <div className="min-h-screen lg:grid lg:grid-cols-[16rem_minmax(0,1fr)]">
        <aside className="border-b border-slate-200 bg-white dark:border-slate-800 dark:bg-slate-900 lg:sticky lg:top-0 lg:h-screen lg:border-b-0 lg:border-r">
          <div className="flex items-center justify-between px-5 py-4 lg:block">
            <div>
              <p className="flex items-center gap-2 text-xl font-bold tracking-tight">
                <span className="grid h-8 w-8 place-items-center rounded-lg bg-indigo-600 text-white" aria-hidden>
                  <ClipboardCheck className="h-5 w-5" />
                </span>
                Benefits Desk
              </p>
            </div>
            <Button variant="ghost" onClick={toggle} aria-label={dark ? "Switch to light theme" : "Switch to dark theme"} className="lg:mt-3">
              {dark ? <Sun className="h-5 w-5" aria-hidden /> : <Moon className="h-5 w-5" aria-hidden />}
              <span className="hidden text-sm lg:inline">{dark ? "Light theme" : "Dark theme"}</span>
            </Button>
          </div>
          <nav aria-label="Screens" className="overflow-x-auto px-3 pb-3 lg:pb-0">
            <ul className="flex gap-1 lg:flex-col">
              {TABS.map((t, i) => (
                <li key={t.id}>
                  <button
                    type="button"
                    onClick={() => setTab(t.id)}
                    aria-current={tab === t.id ? "page" : undefined}
                    className={cx(
                      "flex w-full items-center gap-3 whitespace-nowrap rounded-lg px-3 py-2.5 text-left font-medium transition-colors",
                      tab === t.id ? "bg-indigo-50 text-indigo-800 dark:bg-indigo-950 dark:text-indigo-200" : "text-slate-700 hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-slate-800",
                    )}
                  >
                    {t.icon}
                    <span>
                      <span className="mr-1 text-sm text-slate-400">{i + 1}</span>
                      {t.label}
                    </span>
                  </button>
                </li>
              ))}
            </ul>
          </nav>
        </aside>

        <div className="min-w-0">
          <header className="border-b border-slate-200 bg-white/80 px-6 py-4 backdrop-blur dark:border-slate-800 dark:bg-slate-900/80">
            <div className="flex flex-wrap items-end justify-between gap-4">
              <div>
                <h1 className="text-2xl font-bold tracking-tight">Benefits Desk</h1>
                <p className="text-slate-600 dark:text-slate-400">A tool for a licensed broker. Nothing is bought or sent without the person's approval.</p>
              </div>
              {current.caseView && (
                <div className="flex flex-wrap items-center gap-2">
                  <label htmlFor="run-picker" className="text-sm font-semibold text-slate-700 dark:text-slate-300">
                    Case file
                  </label>
                  <select
                    id="run-picker"
                    value={caseRun ?? ""}
                    onChange={(e) => setCaseRun(e.target.value || null)}
                    className="max-w-[26rem] rounded-lg border border-slate-300 bg-white px-3 py-2 text-base dark:border-slate-600 dark:bg-slate-800"
                  >
                    <option value="">Choose a run…</option>
                    {(runs.data ?? []).map((r) => (
                      <option key={r.run_id} value={r.run_id}>
                        {r.request_id} · {r.type} · {r.status} · {fmtDate(r.started)}
                      </option>
                    ))}
                  </select>
                  <Button variant="ghost" onClick={() => caseQ.reload()} aria-label="Reload case file" disabled={!caseRun}>
                    <RefreshCw className="h-5 w-5" aria-hidden />
                  </Button>
                </div>
              )}
            </div>
          </header>

          <main id="main" className="px-6 py-6">
            <h2 className="sr-only">{current.label}</h2>
            {down && (
              <div className="mb-6">
                <BackendDown />
              </div>
            )}
            <div hidden={tab !== "console"}>
              <RunConsole runs={runs.data} onOpenCase={openCase} onRunsChanged={() => runs.reload(true)} />
            </div>
            {current.caseView && (
              <CaseScreen down={down} tab={tab} caseRun={caseRun} q={caseQ} onGoConsole={() => setTab("console")} hasRuns={(runs.data?.length ?? 0) > 0} runsLoading={runs.loading} />
            )}
          </main>
        </div>
      </div>
    </DrawerProvider>
  );
}

function CaseScreen({
  down,
  tab,
  caseRun,
  q,
  onGoConsole,
  hasRuns,
  runsLoading,
}: {
  down: boolean;
  tab: Tab;
  caseRun: string | null;
  q: { data: CaseFile | { status: "running" } | undefined; error: unknown; loading: boolean; reload: (quiet?: boolean) => void };
  onGoConsole: () => void;
  hasRuns: boolean;
  runsLoading: boolean;
}) {
  // Approvals is useful without a case file (it lists every intent).
  if (tab === "approvals") {
    return <ApprovalsScreen caseFile={isCaseFile(q.data) ? q.data : null} runId={caseRun} />;
  }
  if (!caseRun) {
    if (down) return null;
    if (runsLoading) return <Loading />;
    return (
      <Empty title={hasRuns ? "Choose a case file" : "No finished runs yet"}>
        {hasRuns ? "Pick a run from the Case file menu above." : "Run a prepared request from the Run console first."}
        <div className="mt-3">
          <Button variant="primary" onClick={onGoConsole}>
            Go to Run console
          </Button>
        </div>
      </Empty>
    );
  }
  if (q.loading && !q.data) return <Loading label="Loading case file…" />;
  if (q.error && down) return null;
  if (q.error) return <ErrorState error={q.error} onRetry={() => q.reload()} />;
  if (!q.data) return null;
  if (!isCaseFile(q.data)) {
    return (
      <Empty title="This run is still going">
        The case file appears when the run finishes. Watch it on the Run console.
        <div className="mt-3 flex justify-center gap-2">
          <Button variant="primary" onClick={onGoConsole}>
            Go to Run console
          </Button>
          <Button onClick={() => q.reload()}>Check again</Button>
        </div>
      </Empty>
    );
  }
  const c = q.data;
  return (
    <div className="space-y-6">
      <CaseHeader c={c} />
      <div className="grid gap-6 2xl:grid-cols-[minmax(0,1fr)_22rem] xl:grid-cols-[minmax(0,1fr)_20rem]">
        <div className="min-w-0 space-y-6">
          {tab === "persona" && <PersonaScreen c={c} onChanged={() => q.reload(true)} />}
          {tab === "workplace" && <WorkplaceScreen c={c} />}
          {tab === "gaps" && <GapsScreen c={c} />}
          {tab === "employer" && <EmployerScreen c={c} />}
        </div>
        <CaseAside c={c} />
      </div>
    </div>
  );
}
