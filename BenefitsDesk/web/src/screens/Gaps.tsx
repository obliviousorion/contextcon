import { AlarmClock, AlertTriangle, ArrowRight, Award, CalendarClock, Receipt } from "lucide-react";
import type { Action, CaseFile, Fact, Figure, Gap } from "../types";
import { fmtDate, humanize } from "../format";
import { Badge, Card, Empty, LabelIcon, LABEL_META, SourceButton, cx, useDrawer, LabelTag } from "../components/ui";

const SEV: Record<Gap["severity"], { tone: "red" | "amber" | "slate"; text: string }> = {
  high: { tone: "red", text: "High" },
  medium: { tone: "amber", text: "Medium" },
  low: { tone: "slate", text: "Low" },
};

export function GapsScreen({ c }: { c: CaseFile }) {
  const factMap = new Map((c.facts ?? []).map((f) => [f.fact_id, f]));
  const gaps = c.gaps ?? [];
  const shortlist = [...(c.shortlist ?? [])].sort((a, b) => (a.rank ?? 1e9) - (b.rank ?? 1e9));
  return (
    <>
      {c.alarm && <AlarmCard alarm={c.alarm} conversion={(c.actions ?? []).find((a) => a.action === "conversion_request")} />}

      <Card title="Cover gaps" icon={<Receipt className="h-5 w-5 text-indigo-600 dark:text-indigo-400" aria-hidden />} subtitle="Each line is one rule from the rules file, checked against the fact file.">
        {gaps.length === 0 ? (
          <Empty title="No cover gaps found">Nothing in the rules file flagged this fact file.</Empty>
        ) : (
          <div className="mx-auto max-w-3xl rounded-lg border border-slate-300 bg-[#fffef8] px-5 py-4 font-mono shadow-inner dark:border-slate-700 dark:bg-slate-950">
            <p className="text-center text-sm uppercase tracking-[0.3em] text-slate-500">Gap check · {gaps.length} line{gaps.length > 1 ? "s" : ""}</p>
            <ol className="mt-2">
              {gaps.map((g, i) => (
                <li key={`${g.rule_id}-${i}`} className="border-t border-dashed border-slate-400 py-4 first:border-t-0 dark:border-slate-600">
                  <div className="flex flex-wrap items-baseline justify-between gap-2">
                    <span className="font-semibold text-slate-900 dark:text-slate-100">
                      {String(i + 1).padStart(2, "0")} · {g.cover}
                    </span>
                    <span className="flex items-center gap-2">
                      <span className="text-sm text-slate-500 dark:text-slate-400">{g.rule_id}</span>
                      <Badge tone={SEV[g.severity]?.tone ?? "slate"} className="font-sans">
                        {SEV[g.severity]?.text ?? g.severity} severity
                      </Badge>
                    </span>
                  </div>
                  <div className="mt-2 grid items-center gap-2 font-sans sm:grid-cols-[1fr_auto_1fr]">
                    <div className="rounded-md bg-slate-100 px-3 py-2 dark:bg-slate-800">
                      <p className="text-xs font-bold uppercase text-slate-500 dark:text-slate-400">Held now</p>
                      <p className="text-slate-900 dark:text-slate-100">{g.held}</p>
                    </div>
                    <ArrowRight className="mx-auto h-5 w-5 rotate-90 text-slate-400 sm:rotate-0" aria-hidden />
                    <div className="rounded-md bg-indigo-50 px-3 py-2 dark:bg-indigo-950/60">
                      <p className="text-xs font-bold uppercase text-indigo-700 dark:text-indigo-300">Called for</p>
                      <p className="text-slate-900 dark:text-slate-100">{g.called_for}</p>
                    </div>
                  </div>
                  <p className="mt-2 font-sans text-slate-700 dark:text-slate-300">{g.explanation}</p>
                  {g.facts_used.length > 0 && (
                    <div className="mt-2 flex flex-wrap items-center gap-1.5 font-sans">
                      <span className="text-sm text-slate-500 dark:text-slate-400">Facts used:</span>
                      {g.facts_used.map((id) => (
                        <FactRef key={id} id={id} fact={factMap.get(id)} />
                      ))}
                    </div>
                  )}
                </li>
              ))}
            </ol>
          </div>
        )}
      </Card>

      <Card title="Insurer shortlist" icon={<Award className="h-5 w-5 text-indigo-600 dark:text-indigo-400" aria-hidden />} subtitle="Ranked on regulator figures. Every figure opens its source passage.">
        {shortlist.length === 0 ? (
          <Empty title="No shortlist in this case file" />
        ) : (
          <div className="grid gap-4 2xl:grid-cols-2">
            {shortlist.map((ins) => (
              <article key={ins.insurer} className="flex flex-col rounded-xl border border-slate-200 p-4 dark:border-slate-700">
                <div className="flex items-center justify-between gap-2">
                  <h3 className="text-lg font-semibold">{ins.insurer}</h3>
                  {ins.rank !== null ? <Badge tone="violet">Rank #{ins.rank}</Badge> : <Badge tone="slate">Unranked</Badge>}
                </div>
                <ul className="mt-3 space-y-2">
                  {ins.figures.map((f, i) => (
                    <FigureRow key={i} f={f} insurer={ins.insurer} />
                  ))}
                </ul>
                {ins.reasons.length > 0 && (
                  <ul className="mt-3 list-disc space-y-1 pl-5 text-slate-700 dark:text-slate-300">
                    {ins.reasons.map((r, i) => (
                      <li key={i}>{r}</li>
                    ))}
                  </ul>
                )}
              </article>
            ))}
          </div>
        )}
      </Card>
    </>
  );
}

function FigureRow({ f, insurer }: { f: Figure; insurer: string }) {
  if (f.cannot_verify) {
    return (
      <li className="flex overflow-hidden rounded-lg border-2 border-dashed border-amber-500 bg-amber-50 dark:bg-amber-950/50">
        <span className="hatch w-3 shrink-0" aria-hidden />
        <div className="px-3 py-2">
        <p className="text-sm font-medium text-slate-700 dark:text-slate-300">{f.metric}</p>
        <p className="flex items-center gap-1.5 font-semibold text-amber-900 dark:text-amber-200">
          <AlertTriangle className="h-4 w-4 shrink-0" aria-hidden /> Cannot verify — missing: {f.missing ?? "source not given"}
        </p>
        </div>
      </li>
    );
  }
  return (
    <li className="flex flex-wrap items-center justify-between gap-x-3 gap-y-1 rounded-lg bg-slate-50 px-3 py-2 dark:bg-slate-800/60">
      <div className="min-w-0">
        <p className="text-sm text-slate-600 dark:text-slate-400">
          {f.metric}
          {f.period && <span> · {f.period}</span>}
        </p>
        <p className="text-xl font-semibold tabular-nums">{f.value ?? "—"}</p>
      </div>
      {f.source ? <SourceButton source={f.source} title={`${insurer}: ${f.metric}`}>Source passage</SourceButton> : <span className="text-sm text-amber-700 dark:text-amber-300">No source</span>}
    </li>
  );
}

function FactRef({ id, fact }: { id: string; fact?: Fact }) {
  const { open } = useDrawer();
  if (!fact) {
    return <span className="rounded-md border border-slate-300 px-2 py-0.5 font-mono text-sm text-slate-600 dark:border-slate-600 dark:text-slate-400">{id}</span>;
  }
  const m = LABEL_META[fact.label] ?? LABEL_META.guessed;
  return (
    <button
      type="button"
      onClick={() =>
        open({
          title: fact.statement,
          source: fact.source,
          extra: (
            <div className="space-y-2">
              <LabelTag label={fact.label} />
              <p className="font-mono text-lg">{typeof fact.value === "object" ? JSON.stringify(fact.value) : String(fact.value)}</p>
            </div>
          ),
        })
      }
      className={cx("inline-flex items-center gap-1 rounded-md px-2 py-0.5 text-sm ring-1 ring-inset", m.cls, fact.label === "guessed" && "border border-dashed border-amber-500")}
      title={`${m.text}: ${fact.statement}`}
    >
      <LabelIcon label={fact.label} className="h-3.5 w-3.5" />
      <span className="font-semibold">{m.text}</span>
      <span>· {fact.statement}</span>
    </button>
  );
}

function AlarmCard({ alarm, conversion }: { alarm: NonNullable<CaseFile["alarm"]>; conversion?: Action }) {
  const isChange = alarm.status === "job_change";
  return (
    <section
      className={cx(
        "rounded-2xl border-2 p-5",
        isChange ? "border-red-500 bg-red-50 dark:border-red-700 dark:bg-red-950/40" : "border-slate-300 bg-white dark:border-slate-700 dark:bg-slate-900",
      )}
      aria-labelledby="alarm-h"
    >
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h2 id="alarm-h" className="flex items-center gap-2 text-lg font-semibold">
          <AlarmClock className={cx("h-6 w-6", isChange ? "text-red-600 dark:text-red-400" : "text-slate-500")} aria-hidden />
          Cover-gap alarm
        </h2>
        <Badge tone={isChange ? "red" : alarm.status === "cannot_verify" ? "amber" : "slate"}>{humanize(alarm.status)}</Badge>
      </div>
      {(alarm.old_employer || alarm.new_employer) && (
        <p className="mt-3 flex flex-wrap items-center gap-2 text-lg">
          <span className="font-semibold">{alarm.old_employer ?? "—"}</span>
          <ArrowRight className="h-5 w-5" aria-hidden />
          <span className="font-semibold">{alarm.new_employer ?? "—"}</span>
          {alarm.change_date && <span className="text-base text-slate-600 dark:text-slate-400">on {fmtDate(alarm.change_date)}</span>}
        </p>
      )}
      {(alarm.cover_end_date || alarm.conversion_deadline) && (
        <div className="mt-3 grid gap-3 sm:grid-cols-2">
          {alarm.cover_end_date && (
            <div className="rounded-xl bg-white p-3 ring-1 ring-red-300 dark:bg-slate-900 dark:ring-red-800">
              <p className="text-sm font-semibold uppercase text-red-700 dark:text-red-300">Old group health cover ends</p>
              <p className="flex items-center gap-2 text-2xl font-bold">
                <CalendarClock className="h-6 w-6" aria-hidden /> {fmtDate(alarm.cover_end_date)}
              </p>
            </div>
          )}
          {alarm.conversion_deadline && (
            <div className="rounded-xl bg-white p-3 ring-1 ring-amber-300 dark:bg-slate-900 dark:ring-amber-800">
              <p className="text-sm font-semibold uppercase text-amber-800 dark:text-amber-300">Convert to individual cover by</p>
              <p className="flex items-center gap-2 text-2xl font-bold">
                <CalendarClock className="h-6 w-6" aria-hidden /> {fmtDate(alarm.conversion_deadline)}
              </p>
            </div>
          )}
        </div>
      )}
      <p className="mt-3 text-slate-800 dark:text-slate-200">{alarm.explanation}</p>
      <div className="mt-2 flex flex-wrap items-center gap-3">
        {alarm.sources.length > 0 && <SourceButton sources={alarm.sources} title="Cover-gap alarm">{alarm.sources.length} source{alarm.sources.length > 1 ? "s" : ""}</SourceButton>}
        {conversion && (
          <span className="text-sm text-slate-700 dark:text-slate-300">
            Conversion request prepared · status <Badge tone="amber">{humanize(conversion.status)}</Badge> · see Approvals
          </span>
        )}
      </div>
    </section>
  );
}
