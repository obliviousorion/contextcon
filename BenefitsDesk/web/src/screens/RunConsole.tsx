import { useEffect, useMemo, useRef, useState } from "react";
import { CheckCircle2, CircleDot, FileText, Hand, OctagonX, Play, Recycle, RotateCcw, ShieldCheck, Skull, XCircle, Flag, Activity } from "lucide-react";
import { api } from "../api";
import { useAsync, useInterval } from "../hooks";
import type { EventStatus, Ledger, RunEvent, RunSummary, SandboxReceipt } from "../types";
import { fmtNum, fmtTime, humanize } from "../format";
import { Badge, Button, Card, Empty, ErrorState, Loading, cx } from "../components/ui";
import type { Tab } from "../App";

type Phase = "idle" | "starting" | "running" | "killed" | "finished" | "held" | "failed";

const STATUS_META: Record<EventStatus, { icon: JSX.Element; label: string; cls: string }> = {
  start: { icon: <CircleDot className="h-5 w-5 text-sky-600 dark:text-sky-400" aria-hidden />, label: "Started", cls: "" },
  done: { icon: <CheckCircle2 className="h-5 w-5 text-emerald-600 dark:text-emerald-400" aria-hidden />, label: "Done", cls: "" },
  skipped: { icon: <Recycle className="h-5 w-5 text-slate-500" aria-hidden />, label: "Skipped", cls: "" },
  held: { icon: <Hand className="h-5 w-5 text-amber-600 dark:text-amber-400" aria-hidden />, label: "Held", cls: "" },
  failed: { icon: <XCircle className="h-5 w-5 text-red-600 dark:text-red-400" aria-hidden />, label: "Failed", cls: "" },
  killed: { icon: <Skull className="h-5 w-5 text-red-600 dark:text-red-400" aria-hidden />, label: "Killed", cls: "" },
  finished: { icon: <Flag className="h-5 w-5 text-emerald-600 dark:text-emerald-400" aria-hidden />, label: "Finished", cls: "" },
};

function phaseFromRunStatus(s: string): Phase {
  if (s === "running") return "running";
  if (s === "finished") return "finished";
  if (s === "held") return "held";
  if (s === "killed" || s === "stopped") return "killed";
  if (s === "failed" || s === "refused") return "failed";
  return "idle";
}

export function RunConsole({ runs, onOpenCase, onRunsChanged }: { runs: RunSummary[] | undefined; onOpenCase: (runId: string, tab: Tab) => void; onRunsChanged: () => void }) {
  const reqs = useAsync(() => api.requests(), []);
  const [file, setFile] = useState<string | null>(null);
  const [runId, setRunId] = useState<string | null>(null);
  const [phase, setPhase] = useState<Phase>("idle");
  const [events, setEvents] = useState<RunEvent[]>([]);
  const [actionError, setActionError] = useState<unknown>(null);
  const [ledger, setLedger] = useState<Ledger | null>(null);
  const [killNote, setKillNote] = useState<string | null>(null);
  const [resumes, setResumes] = useState(0);
  const [resumeMarks, setResumeMarks] = useState<number[]>([]);
  const esRef = useRef<EventSource | null>(null);
  const seen = useRef<Set<string>>(new Set());
  const listEnd = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!file && reqs.data && reqs.data.length) setFile(reqs.data[0].file);
  }, [reqs.data, file]);

  const closeStream = () => {
    esRef.current?.close();
    esRef.current = null;
  };

  const openStream = (id: string) => {
    closeStream();
    const es = new EventSource(`/api/stream?run_id=${encodeURIComponent(id)}`);
    esRef.current = es;
    es.onmessage = (m) => {
      let ev: RunEvent;
      try {
        ev = JSON.parse(m.data);
      } catch {
        return;
      }
      const k = `${ev.id ?? ""}|${ev.ts}|${ev.step}|${ev.status}`;
      if (seen.current.has(k)) return;
      seen.current.add(k);
      setEvents((prev) => [...prev, ev]);
      if (ev.status === "finished") {
        setPhase("finished");
        closeStream();
        onRunsChanged();
      } else if (ev.status === "killed") {
        setPhase("killed");
        closeStream();
        onRunsChanged();
      } else if (ev.status === "held") {
        setPhase((p) => (p === "running" || p === "starting" ? "running" : p));
      } else if (ev.status === "failed" && ev.step === "run") {
        setPhase("failed");
      } else {
        setPhase((p) => (p === "starting" || p === "idle" || p === "killed" ? "running" : p));
      }
    };
    es.onerror = () => {
      // EventSource retries on its own; if the server closed the stream for good, stop.
      if (es.readyState === EventSource.CLOSED) closeStream();
    };
  };

  useEffect(() => () => closeStream(), []);

  useEffect(() => {
    listEnd.current?.scrollIntoView({ block: "nearest", behavior: "smooth" });
  }, [events.length]);

  const refreshLedger = async (id: string) => {
    try {
      setLedger(await api.ledger(id));
    } catch {
      /* banner handles backend down */
    }
  };

  useInterval(() => runId && refreshLedger(runId), phase === "running" || phase === "starting" ? 2000 : null);
  useEffect(() => {
    if (runId && phase !== "running") refreshLedger(runId);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [runId, phase]);

  const start = async () => {
    if (!file) return;
    setActionError(null);
    setKillNote(null);
    setEvents([]);
    seen.current = new Set();
    setLedger(null);
    setResumes(0);
    setResumeMarks([]);
    setPhase("starting");
    try {
      const r = await api.run(file);
      setRunId(r.run_id);
      openStream(r.run_id);
      onRunsChanged();
    } catch (e) {
      setActionError(e);
      setPhase("idle");
    }
  };

  const kill = async () => {
    if (!runId) return;
    setActionError(null);
    try {
      const r = await api.kill(runId);
      setKillNote(r.killed ? "Process killed (SIGKILL). Nothing after this point ran." : "No live process to kill — the run had already stopped.");
      if (r.killed) setPhase("killed");
      onRunsChanged();
    } catch (e) {
      setActionError(e);
    }
  };

  const resume = async () => {
    if (!runId) return;
    setActionError(null);
    setKillNote(null);
    try {
      const r = await api.resume(runId);
      setResumes((n) => n + 1);
      setResumeMarks((m) => [...m, events.length]);
      setRunId(r.run_id);
      setPhase("running");
      openStream(r.run_id);
      onRunsChanged();
    } catch (e) {
      setActionError(e);
    }
  };

  const attach = (id: string) => {
    const r = runs?.find((x) => x.run_id === id);
    setActionError(null);
    setKillNote(null);
    setEvents([]);
    seen.current = new Set();
    setLedger(null);
    setResumes(0);
    setResumeMarks([]);
    setRunId(id);
    setPhase(r ? phaseFromRunStatus(r.status) : "running");
    openStream(id);
  };

  const counts = useMemo(() => {
    const c: Partial<Record<EventStatus, number>> = {};
    events.forEach((e) => (c[e.status] = (c[e.status] ?? 0) + 1));
    return c;
  }, [events]);

  const running = phase === "running" || phase === "starting";
  const canResume = !!runId && (phase === "killed" || phase === "failed");

  return (
    <div className="space-y-6">
      <div className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_22rem]">
        <Card title="1 · Pick a prepared request" subtitle="Each one is a file in requests/ on the server.">
          {reqs.loading && <Loading />}
          {!!reqs.error && <ErrorState error={reqs.error} onRetry={() => reqs.reload()} />}
          {reqs.data && reqs.data.length === 0 && <Empty title="No prepared requests">Add a request file under requests/ on the server.</Empty>}
          {reqs.data && reqs.data.length > 0 && (
            <fieldset>
              <legend className="sr-only">Prepared requests</legend>
              <div className="grid gap-3 md:grid-cols-2">
                {reqs.data.map((r) => (
                  <label
                    key={r.file}
                    className={cx(
                      "flex cursor-pointer gap-3 rounded-xl border p-4 transition-colors focus-within:ring-2 focus-within:ring-indigo-500",
                      file === r.file ? "border-indigo-500 bg-indigo-50 dark:border-indigo-400 dark:bg-indigo-950/40" : "border-slate-200 hover:border-slate-400 dark:border-slate-700 dark:hover:border-slate-500",
                    )}
                  >
                    <input type="radio" name="request" className="mt-1 h-4 w-4 accent-indigo-600" checked={file === r.file} onChange={() => setFile(r.file)} disabled={running} />
                    <span className="min-w-0">
                      <span className="flex flex-wrap items-center gap-2">
                        <Badge tone="violet">{humanize(r.type)}</Badge>
                        <span className="font-mono text-sm text-slate-500 dark:text-slate-400">{r.id}</span>
                      </span>
                      <span className="mt-1 block text-slate-900 dark:text-slate-100">“{r.said}”</span>
                    </span>
                  </label>
                ))}
              </div>
            </fieldset>
          )}
          {runs && runs.length > 0 && (
            <div className="mt-4 flex flex-wrap items-center gap-2 border-t border-slate-100 pt-4 dark:border-slate-800">
              <label htmlFor="attach" className="text-sm font-medium text-slate-700 dark:text-slate-300">
                Or watch an existing run:
              </label>
              <select
                id="attach"
                className="rounded-lg border border-slate-300 bg-white px-2 py-1.5 text-base dark:border-slate-600 dark:bg-slate-800"
                value=""
                onChange={(e) => e.target.value && attach(e.target.value)}
              >
                <option value="">Choose a run…</option>
                {runs.map((r) => (
                  <option key={r.run_id} value={r.run_id}>
                    {r.run_id} · {r.request_id} · {r.status}
                  </option>
                ))}
              </select>
            </div>
          )}
        </Card>

        <Card title="2 · Control" subtitle="The backend runs headless. This is a window onto it.">
          <div className="space-y-3">
            <Button variant="primary" className="w-full py-3 text-lg" onClick={start} disabled={!file || running}>
              <Play className="h-5 w-5" aria-hidden /> Run
            </Button>
            <Button variant="danger" className="w-full py-4 text-lg shadow-lg shadow-red-600/20" onClick={kill} disabled={!runId || !running} aria-describedby="kill-hint">
              <OctagonX className="h-6 w-6" aria-hidden /> Kill process
            </Button>
            <p id="kill-hint" className="text-sm text-slate-600 dark:text-slate-400">
              Sends SIGKILL to the run. Resume restarts it; finished steps are reused, not repeated.
            </p>
            <Button variant="secondary" className="w-full py-3 text-lg" onClick={resume} disabled={!canResume}>
              <RotateCcw className="h-5 w-5" aria-hidden /> Resume
            </Button>
            {killNote && (
              <p role="status" className="rounded-lg bg-red-50 px-3 py-2 text-sm font-medium text-red-900 dark:bg-red-950 dark:text-red-100">
                {killNote}
              </p>
            )}
            {!!actionError && <ErrorState error={actionError} />}
          </div>
        </Card>
      </div>

      <div className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_22rem]">
        <Card
          title={
            <>
              <Activity className="h-5 w-5 text-indigo-600 dark:text-indigo-400" aria-hidden /> Live steps
            </>
          }
          subtitle={runId ? <span className="font-mono">{runId}</span> : "Start a run to see its steps arrive here."}
          actions={
            runId && (
              <>
                <PhaseBadge phase={phase} />
                {resumes > 0 && <Badge tone="violet">Resumed ×{resumes}</Badge>}
              </>
            )
          }
        >
          {!runId && <Empty title="No run yet" icon={<Activity className="h-8 w-8" aria-hidden />}>Pick a request and press Run.</Empty>}
          {runId && events.length === 0 && <Loading label="Waiting for the first step…" />}
          {events.length > 0 && (
            <>
              <div className="mb-3 flex flex-wrap gap-2 text-sm" aria-label="Step counts">
                <Badge tone="green">{counts.done ?? 0} done</Badge>
                <Badge tone="slate">
                  <Recycle className="h-3.5 w-3.5" aria-hidden /> {counts.skipped ?? 0} reused
                </Badge>
                {!!counts.held && <Badge tone="amber">{counts.held} held</Badge>}
                {!!counts.failed && <Badge tone="red">{counts.failed} failed</Badge>}
              </div>
              <ol className="max-h-[32rem] space-y-1.5 overflow-y-auto pr-1" aria-live="polite" aria-relevant="additions">
                {events.map((ev, i) => {
                  const prev = events[i - 1];
                  const restarted = resumeMarks.includes(i) || (!!prev && prev.status === "killed");
                  return (
                    <li key={`${ev.id}-${i}`}>
                      {restarted && (
                        <div className="my-3 flex items-center gap-3 text-sm font-semibold text-violet-700 dark:text-violet-300" role="separator">
                          <span className="h-px flex-1 bg-violet-300 dark:bg-violet-700" />
                          Process restarted — resuming from the step store
                          <span className="h-px flex-1 bg-violet-300 dark:bg-violet-700" />
                        </div>
                      )}
                      <EventRow ev={ev} />
                    </li>
                  );
                })}
              </ol>
              <div ref={listEnd} />
            </>
          )}
          {phase === "finished" && runId && (
            <div className="mt-4 rounded-xl border border-emerald-300 bg-emerald-50 p-4 dark:border-emerald-800 dark:bg-emerald-950/50">
              <p className="mb-3 flex items-center gap-2 font-semibold text-emerald-900 dark:text-emerald-100">
                <FileText className="h-5 w-5" aria-hidden /> Case file ready
              </p>
              <div className="flex flex-wrap gap-2">
                {(
                  [
                    ["persona", "Persona"],
                    ["workplace", "Workplace"],
                    ["gaps", "Gaps & shortlist"],
                    ["approvals", "Approvals"],
                    ["employer", "Employer view"],
                  ] as [Tab, string][]
                ).map(([t, l]) => (
                  <Button key={t} variant="secondary" onClick={() => onOpenCase(runId, t)}>
                    {l}
                  </Button>
                ))}
              </div>
            </div>
          )}
        </Card>

        <div className="space-y-6">
          <CostMeter ledger={ledger} live={running} />
          <ExactlyOnce runId={runId} phase={phase} />
        </div>
      </div>

      <Card title="Ledger" subtitle="Every paid call this run made. Cache hits cost nothing.">
        {!runId ? (
          <Empty title="No run selected">The ledger fills in as the run calls data endpoints.</Empty>
        ) : !ledger ? (
          <Loading />
        ) : ledger.rows.length === 0 ? (
          <Empty title="No calls yet" />
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left">
              <thead className="border-b border-slate-200 text-sm text-slate-600 dark:border-slate-700 dark:text-slate-400">
                <tr>
                  <th className="py-2 pr-4 font-semibold">Time</th>
                  <th className="py-2 pr-4 font-semibold">Step</th>
                  <th className="py-2 pr-4 font-semibold">Endpoint</th>
                  <th className="py-2 pr-4 text-right font-semibold">Credits</th>
                  <th className="py-2 pr-4 text-right font-semibold">₹</th>
                  <th className="py-2 pr-4 font-semibold">Cache</th>
                  <th className="py-2 font-semibold">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                {ledger.rows.map((r, i) => (
                  <tr key={i} className="animate-slide-in">
                    <td className="py-2 pr-4 tabular-nums text-slate-600 dark:text-slate-400">{fmtTime(r.ts)}</td>
                    <td className="py-2 pr-4 font-mono text-sm">{r.step}</td>
                    <td className="py-2 pr-4 font-mono text-sm">{r.endpoint}</td>
                    <td className="py-2 pr-4 text-right tabular-nums">{fmtNum(r.credits, 2)}</td>
                    <td className="py-2 pr-4 text-right tabular-nums">{fmtNum(r.inr, 2)}</td>
                    <td className="py-2 pr-4">{r.cache_hit ? <Badge tone="green">Hit · free</Badge> : <Badge tone="slate">Miss</Badge>}</td>
                    <td className="py-2">{r.status}</td>
                  </tr>
                ))}
              </tbody>
              <tfoot className="border-t-2 border-slate-300 font-semibold dark:border-slate-600">
                <tr>
                  <td className="py-2 pr-4" colSpan={3}>
                    Total · {fmtNum(ledger.total.calls)} calls · {fmtNum(ledger.total.cache_hits)} cache hits
                  </td>
                  <td className="py-2 pr-4 text-right tabular-nums">{fmtNum(ledger.total.credits, 2)}</td>
                  <td className="py-2 pr-4 text-right tabular-nums">{fmtNum(ledger.total.inr, 2)}</td>
                  <td colSpan={2} />
                </tr>
              </tfoot>
            </table>
          </div>
        )}
      </Card>
    </div>
  );
}

function PhaseBadge({ phase }: { phase: Phase }) {
  const m: Record<Phase, [string, "slate" | "blue" | "red" | "green" | "amber"]> = {
    idle: ["Idle", "slate"],
    starting: ["Starting…", "blue"],
    running: ["Running", "blue"],
    killed: ["Killed", "red"],
    finished: ["Finished", "green"],
    held: ["Held", "amber"],
    failed: ["Failed", "red"],
  };
  const [l, t] = m[phase];
  return (
    <Badge tone={t}>
      {phase === "running" && <span className="h-2 w-2 animate-pulse rounded-full bg-sky-600" aria-hidden />}
      {l}
    </Badge>
  );
}

function EventRow({ ev }: { ev: RunEvent }) {
  const meta = STATUS_META[ev.status] ?? STATUS_META.start;
  if (ev.status === "skipped") {
    return (
      <div className="flex animate-skip-in items-start gap-3 rounded-lg border border-dashed border-slate-300 bg-slate-50 px-3 py-2 dark:border-slate-700 dark:bg-slate-900/60">
        <span className="mt-0.5">{meta.icon}</span>
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-2">
            <span className="font-mono text-slate-600 line-through decoration-slate-400/60 dark:text-slate-400">{ev.step}</span>
            <span className="rounded bg-slate-200 px-1.5 py-0.5 text-xs font-bold uppercase tracking-wide text-slate-700 dark:bg-slate-700 dark:text-slate-200">Skipped · reused from step store</span>
          </div>
          {ev.msg && <p className="text-sm text-slate-500 dark:text-slate-400">{ev.msg}</p>}
        </div>
        <time className="shrink-0 text-sm tabular-nums text-slate-400">{fmtTime(ev.ts)}</time>
      </div>
    );
  }
  const strong = ev.status === "killed" || ev.status === "failed";
  return (
    <div
      className={cx(
        "flex animate-slide-in items-start gap-3 rounded-lg px-3 py-2",
        strong && "border border-red-300 bg-red-50 dark:border-red-800 dark:bg-red-950/50",
        ev.status === "held" && "border border-amber-300 bg-amber-50 dark:border-amber-800 dark:bg-amber-950/40",
        ev.status === "finished" && "border border-emerald-300 bg-emerald-50 dark:border-emerald-800 dark:bg-emerald-950/40",
      )}
    >
      <span className="mt-0.5">{meta.icon}</span>
      <div className="min-w-0 flex-1">
        <div className="flex flex-wrap items-center gap-2">
          <span className="font-mono font-medium text-slate-900 dark:text-slate-100">{ev.step}</span>
          <span className="text-sm font-semibold text-slate-600 dark:text-slate-400">{meta.label}</span>
        </div>
        {ev.msg && <p className="text-slate-700 dark:text-slate-300">{ev.msg}</p>}
      </div>
      <time className="shrink-0 text-sm tabular-nums text-slate-500 dark:text-slate-400">{fmtTime(ev.ts)}</time>
    </div>
  );
}

function CostMeter({ ledger, live }: { ledger: Ledger | null; live: boolean }) {
  const spent = ledger?.total.credits ?? 0;
  const cap = ledger?.cap ?? 0;
  const pct = cap > 0 ? Math.min(100, (spent / cap) * 100) : 0;
  const over = pct >= 90;
  return (
    <Card title="Cost meter" subtitle={live ? "Updating every 2 s" : "Credits spent against the run's cap"}>
      {!ledger ? (
        <p className="text-slate-600 dark:text-slate-400">No spend yet.</p>
      ) : (
        <>
          <p className="text-3xl font-semibold tabular-nums">
            {fmtNum(spent, 2)}
            <span className="text-lg font-normal text-slate-500 dark:text-slate-400"> / {fmtNum(cap, 2)} credits</span>
          </p>
          <div className="mt-3 h-4 overflow-hidden rounded-full bg-slate-200 dark:bg-slate-800" role="meter" aria-label="Credits spent against cap" aria-valuemin={0} aria-valuemax={cap} aria-valuenow={spent}>
            <div className={cx("h-full rounded-full transition-[width] duration-700 ease-out", over ? "bg-red-600" : "bg-indigo-600")} style={{ width: `${pct}%` }} />
          </div>
          <p className="mt-1 text-sm text-slate-600 dark:text-slate-400">{fmtNum(pct, 1)}% of cap</p>
          <dl className="mt-3 grid grid-cols-3 gap-2 text-center">
            <div className="rounded-lg bg-slate-50 py-2 dark:bg-slate-800">
              <dt className="text-xs text-slate-600 dark:text-slate-400">Calls</dt>
              <dd className="text-lg font-semibold tabular-nums">{fmtNum(ledger.total.calls)}</dd>
            </div>
            <div className="rounded-lg bg-slate-50 py-2 dark:bg-slate-800">
              <dt className="text-xs text-slate-600 dark:text-slate-400">Cache hits</dt>
              <dd className="text-lg font-semibold tabular-nums">{fmtNum(ledger.total.cache_hits)}</dd>
            </div>
            <div className="rounded-lg bg-slate-50 py-2 dark:bg-slate-800">
              <dt className="text-xs text-slate-600 dark:text-slate-400">₹</dt>
              <dd className="text-lg font-semibold tabular-nums">{fmtNum(ledger.total.inr, 2)}</dd>
            </div>
          </dl>
        </>
      )}
    </Card>
  );
}

function ExactlyOnce({ runId, phase }: { runId: string | null; phase: Phase }) {
  const [rows, setRows] = useState<SandboxReceipt[] | null>(null);
  const [keys, setKeys] = useState<Set<string>>(new Set());
  useEffect(() => {
    if (!runId) return;
    let alive = true;
    (async () => {
      try {
        const [sb, ap] = await Promise.all([api.sandbox(), api.approvals()]);
        if (!alive) return;
        setKeys(new Set(ap.filter((a) => a.run_id === runId).map((a) => a.key)));
        setRows(sb);
      } catch {
        /* banner */
      }
    })();
    return () => {
      alive = false;
    };
  }, [runId, phase]);
  if (!runId) return null;
  const mine = (rows ?? []).filter((r) => keys.has(r.key));
  const dupes = mine.filter((r) => r.count > 1);
  return (
    <Card title="Exactly-once check" icon={<ShieldCheck className="h-5 w-5 text-emerald-600 dark:text-emerald-400" aria-hidden />}>
      {rows === null ? (
        <Loading />
      ) : mine.length === 0 ? (
        <p className="text-slate-600 dark:text-slate-400">Nothing has been sent for this run. Actions wait for the person’s approval.</p>
      ) : dupes.length === 0 ? (
        <p className="font-medium text-emerald-800 dark:text-emerald-200">
          {mine.length} action{mine.length > 1 ? "s" : ""} received by the sandbox, each exactly once. No action repeated.
        </p>
      ) : (
        <p className="font-semibold text-red-700 dark:text-red-300">{dupes.length} action(s) received more than once.</p>
      )}
    </Card>
  );
}
