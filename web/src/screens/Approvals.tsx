import { useState } from "react";
import { CheckCircle2, ClipboardCheck, Inbox, Send, ShieldAlert, ShieldCheck, Undo2, Ban } from "lucide-react";
import { api } from "../api";
import { useAsync, useInterval } from "../hooks";
import type { Action, CaseFile } from "../types";
import { fmtDate, humanize } from "../format";
import { Badge, Button, Card, Empty, ErrorState, Loading, cx } from "../components/ui";
import { CaseAside, CaseHeader, statusTone } from "../components/CaseAside";

export function ApprovalsScreen({ caseFile, runId }: { caseFile: CaseFile | null; runId: string | null }) {
  const approvals = useAsync(() => api.approvals(), []);
  const sandbox = useAsync(() => api.sandbox(), []);
  const [onlyThisRun, setOnlyThisRun] = useState(true);
  useInterval(() => {
    approvals.reload(true);
    sandbox.reload(true);
  }, 3000);

  const list = (approvals.data ?? []).filter((a) => !onlyThisRun || !runId || a.run_id === runId);
  const approvedRuns = [...new Set(list.filter((a) => a.status === "approved").map((a) => a.run_id))];

  const main = (
    <div className="min-w-0 space-y-6">
      <Card
        title="Approval queue"
        icon={<ClipboardCheck className="h-5 w-5 text-indigo-600 dark:text-indigo-400" aria-hidden />}
        subtitle="Nothing is submitted until the person approves it. One approval, one action."
        actions={
          runId && (
            <label className="flex items-center gap-2 text-sm font-medium">
              <input type="checkbox" className="h-4 w-4 accent-indigo-600" checked={onlyThisRun} onChange={(e) => setOnlyThisRun(e.target.checked)} />
              Only this case file’s run
            </label>
          )
        }
      >
        {approvals.loading && !approvals.data && <Loading />}
        {!!approvals.error && <ErrorState error={approvals.error} onRetry={() => approvals.reload()} />}
        {approvals.data && list.length === 0 && (
          <Empty title="Nothing waiting for approval" icon={<Inbox className="h-8 w-8" aria-hidden />}>
            Prepared applications and conversion requests appear here.
          </Empty>
        )}
        <div className="space-y-4">
          {list.map((a) => (
            <ActionCard key={a.key} a={a} onChanged={() => approvals.reload(true)} />
          ))}
        </div>
        {approvedRuns.length > 0 && (
          <div className="mt-4 rounded-xl border border-sky-300 bg-sky-50 p-4 dark:border-sky-800 dark:bg-sky-950/40">
            <p className="mb-2 text-slate-800 dark:text-slate-200">Approved actions are sent by the run (also on resume). You can send them now:</p>
            <div className="flex flex-wrap gap-2">
              {approvedRuns.map((r) => (
                <SendButton key={r} runId={r} onDone={() => { approvals.reload(true); sandbox.reload(true); }} />
              ))}
            </div>
          </div>
        )}
      </Card>

      <Card
        title="Sandbox receipts"
        icon={<ShieldCheck className="h-5 w-5 text-emerald-600 dark:text-emerald-400" aria-hidden />}
        subtitle="What the sandbox receiver actually got. A count of 1 means exactly once."
      >
        {sandbox.loading && !sandbox.data && <Loading />}
        {!!sandbox.error && <ErrorState error={sandbox.error} onRetry={() => sandbox.reload()} />}
        {sandbox.data && sandbox.data.length === 0 && <Empty title="Nothing sent yet">The sandbox has not received any action.</Empty>}
        {sandbox.data && sandbox.data.length > 0 && <SandboxTable rows={sandbox.data} />}
      </Card>
    </div>
  );

  if (!caseFile) return main;
  return (
    <div className="space-y-6">
      <CaseHeader c={caseFile} />
      <div className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_20rem] 2xl:grid-cols-[minmax(0,1fr)_22rem]">
        {main}
        <CaseAside c={caseFile} />
      </div>
    </div>
  );
}

function SendButton({ runId, onDone }: { runId: string; onDone: () => void }) {
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<unknown>(null);
  return (
    <>
      <Button
        variant="primary"
        disabled={busy}
        onClick={async () => {
          setBusy(true);
          setErr(null);
          try {
            await api.act(runId);
          } catch (e) {
            setErr(e);
          } finally {
            setBusy(false);
            onDone();
          }
        }}
      >
        <Send className="h-4 w-4" aria-hidden /> {busy ? "Sending…" : <>Send approved for <span className="font-mono">{runId}</span></>}
      </Button>
      {!!err && <ErrorState error={err} />}
    </>
  );
}

function ActionCard({ a, onChanged }: { a: Action; onChanged: () => void }) {
  const [pending, setPending] = useState(false);
  const [notice, setNotice] = useState<string | null>(null);
  const [err, setErr] = useState<unknown>(null);
  const awaiting = a.status === "awaiting_approval";
  const locked = pending || !awaiting;

  const click = async () => {
    // A second press is still sent, so the server proves it acts once.
    if (pending) {
      setNotice("Already approved — one action only");
    }
    setPending(true);
    setErr(null);
    try {
      const r = await api.approve(a.key);
      if (r.already) setNotice("Already approved — one action only");
      else if (r.approved) setNotice("Approved. It will be sent once.");
      onChanged();
    } catch (e) {
      setErr(e);
    } finally {
      setPending(false);
    }
  };

  return (
    <article className={cx("rounded-xl border p-4", awaiting ? "border-amber-400 dark:border-amber-700" : "border-slate-200 dark:border-slate-700")}>
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            <Badge tone="violet">{humanize(a.action)}</Badge>
            <Badge tone={statusTone(a.status)}>{humanize(a.status)}</Badge>
            <span className="font-mono text-sm text-slate-500 dark:text-slate-400">{a.run_id}</span>
          </div>
          <p className="mt-2 text-sm font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">What will happen</p>
          <p className="text-lg text-slate-900 dark:text-slate-100">{a.summary}</p>
        </div>
        <div className="flex flex-col items-end gap-1">
          <Button
            variant="primary"
            onClick={click}
            aria-disabled={locked}
            className={cx("px-5 py-2.5 text-lg", locked && "cursor-not-allowed opacity-60")}
          >
            <CheckCircle2 className="h-5 w-5" aria-hidden />
            {pending ? "Approving…" : awaiting ? "Approve" : "Approved"}
          </Button>
          {!awaiting && !notice && <span className="text-sm text-slate-500 dark:text-slate-400">Pressing again does nothing new.</span>}
        </div>
      </div>

      <dl className="mt-3 grid gap-3 sm:grid-cols-3">
        <div className="rounded-lg bg-slate-50 px-3 py-2 dark:bg-slate-800/60">
          <dt className="text-sm text-slate-600 dark:text-slate-400">Reversible</dt>
          <dd className="flex items-center gap-1.5 font-semibold">
            {a.reversible ? <Undo2 className="h-4 w-4 text-emerald-600" aria-hidden /> : <Ban className="h-4 w-4 text-red-600" aria-hidden />}
            {a.reversible ? "Yes — can be undone" : "No — cannot be undone"}
          </dd>
        </div>
        <div className="rounded-lg bg-slate-50 px-3 py-2 dark:bg-slate-800/60 sm:col-span-2">
          <dt className="text-sm text-slate-600 dark:text-slate-400">Cost</dt>
          <dd className="font-medium">{a.cost_note || "—"}</dd>
        </div>
      </dl>

      {(a.approved_by || a.approved_at || a.done_at) && (
        <p className="mt-2 text-sm text-slate-600 dark:text-slate-400">
          {a.approved_by && <>Approved by {a.approved_by} </>}
          {a.approved_at && <>at {fmtDate(a.approved_at)} </>}
          {a.done_at && <>· sent {fmtDate(a.done_at)}</>}
        </p>
      )}

      <details className="mt-3 rounded-lg border border-slate-200 dark:border-slate-700" open={awaiting}>
        <summary className="cursor-pointer select-none px-3 py-2 text-sm font-semibold text-slate-700 dark:text-slate-300">Payload preview (exactly what will be sent)</summary>
        <pre className="max-h-64 overflow-auto border-t border-slate-200 bg-slate-50 p-3 font-mono text-sm dark:border-slate-700 dark:bg-slate-950">{JSON.stringify(a.payload, null, 2)}</pre>
      </details>

      {notice && (
        <p role="status" className={cx("mt-3 flex items-center gap-2 rounded-lg px-3 py-2 font-semibold", notice.startsWith("Already") ? "bg-amber-100 text-amber-950 dark:bg-amber-950 dark:text-amber-100" : "bg-emerald-50 text-emerald-900 dark:bg-emerald-950 dark:text-emerald-100")}>
          {notice.startsWith("Already") ? <ShieldAlert className="h-5 w-5" aria-hidden /> : <CheckCircle2 className="h-5 w-5" aria-hidden />}
          {notice}
        </p>
      )}
      {!!err && (
        <div className="mt-3">
          <ErrorState error={err} />
        </div>
      )}
    </article>
  );
}

function SandboxTable({ rows }: { rows: { key: string; received_at: string; action: string; count: number }[] }) {
  const dupes = rows.filter((r) => r.count > 1).length;
  return (
    <>
      <p className={cx("mb-3 rounded-lg px-3 py-2 font-semibold", dupes ? "bg-red-600 text-white" : "bg-emerald-50 text-emerald-900 dark:bg-emerald-950 dark:text-emerald-100")}>
        {dupes ? `${dupes} action(s) were received more than once.` : `${rows.length} action(s) received, each exactly once.`}
      </p>
      <div className="overflow-x-auto">
        <table className="w-full text-left">
          <thead className="border-b border-slate-200 text-sm text-slate-600 dark:border-slate-700 dark:text-slate-400">
            <tr>
              <th className="py-2 pr-4 font-semibold">Action</th>
              <th className="py-2 pr-4 font-semibold">Key</th>
              <th className="py-2 pr-4 font-semibold">Received</th>
              <th className="py-2 text-right font-semibold">Count</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
            {rows.map((r) => (
              <tr key={r.key} className={r.count > 1 ? "bg-red-50 dark:bg-red-950/50" : undefined}>
                <td className="py-2 pr-4">{humanize(r.action)}</td>
                <td className="py-2 pr-4 font-mono text-sm">{r.key}</td>
                <td className="py-2 pr-4 text-sm">{fmtDate(r.received_at)}</td>
                <td className="py-2 text-right">
                  {r.count > 1 ? (
                    <span className="inline-flex items-center gap-1 rounded-full bg-red-600 px-2.5 py-0.5 font-bold text-white">×{r.count} duplicate</span>
                  ) : (
                    <span className="inline-flex items-center gap-1 rounded-full bg-emerald-100 px-2.5 py-0.5 font-bold text-emerald-900 dark:bg-emerald-900 dark:text-emerald-100">
                      ×{r.count} exactly once
                    </span>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </>
  );
}
