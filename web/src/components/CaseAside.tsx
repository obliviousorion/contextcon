import { AlertOctagon, HelpCircle, Recycle, Wallet } from "lucide-react";
import type { CaseFile } from "../types";
import { fmtDate, fmtNum, humanize } from "../format";
import { Badge, Card } from "./ui";

export function statusTone(s: string): "green" | "amber" | "red" | "slate" | "blue" {
  if (s === "finished" || s === "done") return "green";
  if (s === "held" || s === "awaiting_approval" || s === "stopped") return "amber";
  if (s === "refused" || s === "failed" || s === "killed") return "red";
  if (s === "running" || s === "approved" || s === "sending") return "blue";
  return "slate";
}

export function CaseHeader({ c }: { c: CaseFile }) {
  return (
    <div className="flex flex-wrap items-center gap-x-4 gap-y-2 rounded-2xl border border-slate-200 bg-white px-5 py-3 dark:border-slate-800 dark:bg-slate-900">
      <Badge tone={statusTone(c.status)}>{humanize(c.status)}</Badge>
      <span className="font-mono text-sm text-slate-600 dark:text-slate-400">{c.run_id}</span>
      <span className="text-slate-500 dark:text-slate-400">·</span>
      <span className="text-sm text-slate-700 dark:text-slate-300">
        {humanize(c.request.type)} · <span className="font-mono">{c.request.id}</span>
      </span>
      <span className="text-sm text-slate-600 dark:text-slate-400">as of {fmtDate(c.as_of)}</span>
      <p className="basis-full text-slate-800 dark:text-slate-200">
        <span className="text-sm font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">Request said: </span>“{c.request.said}”
      </p>
    </div>
  );
}

export function CaseAside({ c }: { c: CaseFile }) {
  const cost = c.cost;
  const pct = cost && cost.cap > 0 ? Math.min(100, (cost.credits / cost.cap) * 100) : 0;
  return (
    <aside className="space-y-4" aria-label="Cost and open questions">
      {cost && (
        <Card title="Cost" icon={<Wallet className="h-5 w-5 text-indigo-600 dark:text-indigo-400" aria-hidden />}>
          <p className="text-2xl font-semibold tabular-nums">
            {fmtNum(cost.credits, 2)} <span className="text-base font-normal text-slate-500">/ {fmtNum(cost.cap, 2)} credits</span>
          </p>
          <div className="mt-2 h-2.5 overflow-hidden rounded-full bg-slate-200 dark:bg-slate-800" role="meter" aria-valuemin={0} aria-valuemax={cost.cap} aria-valuenow={cost.credits} aria-label="Credits spent against cap">
            <div className={pct > 90 ? "h-full bg-red-600" : "h-full bg-indigo-600"} style={{ width: `${pct}%` }} />
          </div>
          <dl className="mt-3 grid grid-cols-2 gap-2 text-sm">
            <dt className="text-slate-600 dark:text-slate-400">₹ spent</dt>
            <dd className="text-right tabular-nums">{fmtNum(cost.inr, 2)}</dd>
            <dt className="text-slate-600 dark:text-slate-400">Calls</dt>
            <dd className="text-right tabular-nums">{fmtNum(cost.calls)}</dd>
            <dt className="text-slate-600 dark:text-slate-400">Cache hits</dt>
            <dd className="text-right tabular-nums">{fmtNum(cost.cache_hits)}</dd>
            <dt className="text-slate-600 dark:text-slate-400">Seconds</dt>
            <dd className="text-right tabular-nums">{fmtNum(cost.seconds, 1)}</dd>
          </dl>
        </Card>
      )}
      {c.skipped_steps && c.skipped_steps.length > 0 && (
        <Card title="Reused after restart" icon={<Recycle className="h-5 w-5 text-slate-500" aria-hidden />}>
          <p className="mb-2 text-sm text-slate-600 dark:text-slate-400">These steps were already done before the process was stopped, so they were read from the step store, not run again.</p>
          <div className="flex flex-wrap gap-1.5">
            {c.skipped_steps.map((s) => (
              <span key={s} className="rounded-md border border-dashed border-slate-400 px-2 py-0.5 font-mono text-sm text-slate-600 dark:border-slate-600 dark:text-slate-400">
                {s}
              </span>
            ))}
          </div>
        </Card>
      )}
      <Card title="Cannot verify" icon={<AlertOctagon className="h-5 w-5 text-amber-600 dark:text-amber-400" aria-hidden />}>
        {c.cannot_verify && c.cannot_verify.length > 0 ? (
          <ul className="space-y-3">
            {c.cannot_verify.map((x, i) => (
              <li key={i} className="rounded-lg border-l-4 border-amber-500 bg-amber-50 px-3 py-2 dark:bg-amber-950/50">
                <p className="text-slate-900 dark:text-slate-100">{x.statement}</p>
                <p className="text-sm text-amber-900 dark:text-amber-200">
                  <span className="font-semibold">Missing:</span> {x.missing}
                </p>
              </li>
            ))}
          </ul>
        ) : (
          <p className="text-slate-600 dark:text-slate-400">Nothing flagged as unverifiable in this case file.</p>
        )}
      </Card>
      <Card title="Questions for the person" icon={<HelpCircle className="h-5 w-5 text-sky-600 dark:text-sky-400" aria-hidden />}>
        {c.questions && c.questions.length > 0 ? (
          <ol className="list-decimal space-y-3 pl-5">
            {c.questions.map((q, i) => (
              <li key={i}>
                <p className="font-medium text-slate-900 dark:text-slate-100">{q.question}</p>
                <p className="text-sm text-slate-600 dark:text-slate-400">Why: {q.why}</p>
              </li>
            ))}
          </ol>
        ) : (
          <p className="text-slate-600 dark:text-slate-400">No open questions.</p>
        )}
      </Card>
    </aside>
  );
}
