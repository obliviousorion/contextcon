import { AlertTriangle, BarChart3, Building2, ExternalLink, Info, Package, Quote } from "lucide-react";
import type { CaseFile } from "../types";
import { fmtDate, fmtNum, fmtPct } from "../format";
import { Badge, Card, Empty, JsonBlock, SourceButton, Stat } from "../components/ui";

type PB = NonNullable<CaseFile["peer_benchmark"]>;

export function EmployerScreen({ c }: { c: CaseFile }) {
  const pb = c.peer_benchmark;
  const pkg = c.package ?? [];
  if (!pb && pkg.length === 0) {
    return <Empty title="No employer view in this case file" icon={<Building2 className="h-8 w-8" aria-hidden />}>Open a case file from an employer request.</Empty>;
  }
  return (
    <>
      {pb && <Benchmark pb={pb} />}
      {pb?.by_role && pb.by_role.length > 0 && <ByRole rows={pb.by_role} />}
      {pkg.length > 0 && (
        <Card title="Proposed cover package" icon={<Package className="h-5 w-5 text-indigo-600 dark:text-indigo-400" aria-hidden />} subtitle="Per role. Each item names the rule behind it.">
          <div className="grid gap-4 lg:grid-cols-3">
            {pkg.map((p) => (
              <article key={p.role} className="rounded-xl border border-slate-200 p-4 dark:border-slate-700">
                <h3 className="text-lg font-semibold">{p.role}</h3>
                {p.items.length === 0 ? (
                  <p className="mt-2 text-slate-600 dark:text-slate-400">No items proposed.</p>
                ) : (
                  <ul className="mt-2 space-y-3">
                    {p.items.map((it, i) => (
                      <li key={i} className="border-l-4 border-indigo-400 pl-3">
                        <div className="flex flex-wrap items-center gap-2">
                          <span className="font-semibold">{it.cover}</span>
                          <span className="rounded bg-slate-100 px-1.5 py-0.5 font-mono text-xs text-slate-700 dark:bg-slate-800 dark:text-slate-300">{it.rule_id}</span>
                        </div>
                        <p className="text-slate-700 dark:text-slate-300">{it.why}</p>
                      </li>
                    ))}
                  </ul>
                )}
              </article>
            ))}
          </div>
        </Card>
      )}
    </>
  );
}

function Benchmark({ pb }: { pb: PB }) {
  return (
    <Card
      title="Peer benchmark"
      icon={<BarChart3 className="h-5 w-5 text-indigo-600 dark:text-indigo-400" aria-hidden />}
      subtitle={<>Recent logistics job posts in India that mention health cover · as of {fmtDate(pb.as_of)}</>}
      actions={<SourceButton source={pb.source} title="Peer benchmark">Source</SourceButton>}
    >
      <div className="grid gap-3 sm:grid-cols-3">
        <Stat label="Job posts counted" value={fmtNum(pb.total)} />
        <Stat label="Mention any cover" value={fmtNum(pb.any_cover.count)} hint={fmtPct(pb.any_cover.share)} />
        <Stat label="As of" value={<span className="text-lg">{fmtDate(pb.as_of)}</span>} />
      </div>

      <div role="note" className="mt-4 flex items-start gap-2 rounded-lg border-l-4 border-sky-500 bg-sky-50 px-4 py-3 text-sky-950 dark:bg-sky-950/50 dark:text-sky-100">
        <Info className="mt-0.5 h-5 w-5 shrink-0" aria-hidden />
        <p>{pb.note}</p>
      </div>

      <h3 className="mb-2 mt-5 font-semibold">Phrases found, share of all {fmtNum(pb.total)} posts</h3>
      <PhraseBars pb={pb} />

      <div className="mt-4">
        <JsonBlock value={pb.filter} summary="Search filter used (JSON)" />
      </div>

      <h3 className="mb-2 mt-6 flex items-center gap-2 font-semibold">
        <Quote className="h-4 w-4" aria-hidden /> Sample passages
      </h3>
      {pb.samples.length === 0 ? (
        <p className="text-slate-600 dark:text-slate-400">No sample passages.</p>
      ) : (
        <ul className="grid gap-3 lg:grid-cols-2">
          {pb.samples.map((s) => (
            <li key={s.job_id} className="rounded-xl border border-slate-200 p-4 dark:border-slate-700">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <span className="font-semibold">{s.company}</span>
                <span className="text-sm text-slate-600 dark:text-slate-400">{fmtDate(s.date_added)}</span>
              </div>
              <Badge tone="blue" className="mt-1">{s.phrase}</Badge>
              <blockquote className="mt-2 text-slate-800 dark:text-slate-200">“{highlight(s.passage, s.phrase)}”</blockquote>
              <a href={s.url} target="_blank" rel="noreferrer noopener" className="mt-2 inline-flex items-center gap-1 text-sm font-medium text-indigo-700 underline underline-offset-2 dark:text-indigo-300">
                Open job post <ExternalLink className="h-4 w-4" aria-hidden />
              </a>
            </li>
          ))}
        </ul>
      )}
    </Card>
  );
}

function highlight(text: string, phrase: string) {
  if (!phrase) return text;
  const i = text.toLowerCase().indexOf(phrase.toLowerCase());
  if (i < 0) return text;
  return (
    <>
      {text.slice(0, i)}
      <mark className="rounded bg-amber-200 px-0.5 text-slate-950 dark:bg-amber-400">{text.slice(i, i + phrase.length)}</mark>
      {text.slice(i + phrase.length)}
    </>
  );
}

function PhraseBars({ pb }: { pb: PB }) {
  const rows = [...pb.phrases].sort((a, b) => (b.count ?? -1) - (a.count ?? -1));
  const W = 720;
  const labelW = 210;
  const valueW = 120;
  const rowH = 38;
  const barMax = W - labelW - valueW;
  const H = rows.length * rowH + 8;
  const denom = pb.total > 0 ? pb.total : Math.max(1, ...rows.map((r) => r.count ?? 0));
  if (rows.length === 0) return <p className="text-slate-600 dark:text-slate-400">No phrases counted.</p>;
  return (
    <>
      <svg viewBox={`0 0 ${W} ${H}`} className="h-auto w-full" role="img" aria-label="Count of job posts mentioning each phrase">
        {rows.map((r, i) => {
          const y = 4 + i * rowH;
          const share = r.share ?? (r.count !== null ? r.count / denom : null);
          const frac = share === null ? 0 : share <= 1 ? share : share / 100;
          const w = Math.max(r.count ? 2 : 0, frac * barMax);
          return (
            <g key={r.phrase}>
              <title>{r.cannot_verify ? `${r.phrase}: cannot verify (${r.cannot_verify})` : `${r.phrase}: ${r.count} of ${pb.total} posts (${fmtPct(share)})`}</title>
              <text x={labelW - 10} y={y + rowH / 2 - 2} textAnchor="end" dominantBaseline="middle" className="fill-slate-800 text-[14px] dark:fill-slate-200">
                {r.phrase.length > 28 ? r.phrase.slice(0, 27) + "…" : r.phrase}
              </text>
              <rect x={labelW} y={y + 6} width={barMax} height={rowH - 16} rx={4} className="fill-slate-100 dark:fill-slate-800" />
              {r.cannot_verify || r.count === null ? (
                <>
                  <rect x={labelW} y={y + 6} width={barMax} height={rowH - 16} rx={4} className="fill-none stroke-amber-500" strokeDasharray="5 4" />
                  <text x={labelW + 10} y={y + rowH / 2 - 2} dominantBaseline="middle" className="fill-amber-800 text-[13px] font-semibold dark:fill-amber-300">
                    Cannot verify{r.cannot_verify ? ` — ${r.cannot_verify}` : ""}
                  </text>
                </>
              ) : (
                <rect
                  x={labelW}
                  y={y + 6}
                  width={w}
                  height={rowH - 16}
                  rx={4}
                  className="animate-grow-x fill-indigo-600 dark:fill-indigo-400"
                  style={{ transformBox: "fill-box", transformOrigin: "left", animationDelay: `${i * 60}ms` }}
                />
              )}
              {r.count !== null && !r.cannot_verify && (
                <text x={W - valueW + 10} y={y + rowH / 2 - 2} dominantBaseline="middle" className="fill-slate-900 text-[14px] font-semibold dark:fill-slate-100">
                  {fmtNum(r.count)} · {fmtPct(share)}
                </text>
              )}
            </g>
          );
        })}
      </svg>
      {rows.some((r) => r.cannot_verify) && (
        <p className="mt-1 flex items-center gap-1.5 text-sm text-amber-800 dark:text-amber-300">
          <AlertTriangle className="h-4 w-4" aria-hidden /> Dashed rows could not be counted from the source.
        </p>
      )}
    </>
  );
}

function ByRole({ rows }: { rows: NonNullable<PB["by_role"]> }) {
  return (
    <Card title="By role" subtitle="Job posts per role and how many mention health cover.">
      <div className="overflow-x-auto">
        <table className="w-full text-left">
          <thead className="border-b border-slate-200 text-sm text-slate-600 dark:border-slate-700 dark:text-slate-400">
            <tr>
              <th className="py-2 pr-4 font-semibold">Role</th>
              <th className="py-2 pr-4 text-right font-semibold">Posts</th>
              <th className="py-2 pr-4 text-right font-semibold">Mention cover</th>
              <th className="py-2 font-semibold">Share</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
            {rows.map((r) => {
              const share = r.total > 0 ? r.with_cover / r.total : null;
              return (
                <tr key={r.role}>
                  <td className="py-2 pr-4 font-medium">{r.role}</td>
                  <td className="py-2 pr-4 text-right tabular-nums">{fmtNum(r.total)}</td>
                  <td className="py-2 pr-4 text-right tabular-nums">{fmtNum(r.with_cover)}</td>
                  <td className="py-2">
                    <div className="flex items-center gap-2">
                      <div className="h-2.5 w-32 overflow-hidden rounded-full bg-slate-200 dark:bg-slate-800" aria-hidden>
                        <div className="h-full bg-indigo-600 dark:bg-indigo-400" style={{ width: `${(share ?? 0) * 100}%` }} />
                      </div>
                      <span className="tabular-nums">{fmtPct(share)}</span>
                    </div>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </Card>
  );
}
