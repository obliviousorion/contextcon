import { useEffect, useMemo, useState } from "react";
import { EyeOff, History, Users } from "lucide-react";
import { api } from "../api";
import { useAsync } from "../hooks";
import type { Belief, CaseFile } from "../types";
import { fmtDate, fmtNum } from "../format";
import { Badge, Card, Empty, ErrorState, Loading, SourceButton } from "../components/ui";

type Timeline = NonNullable<CaseFile["workplace"]>["timeline"];

export function WorkplaceScreen({ c }: { c: CaseFile }) {
  const w = c.workplace;
  const hist = useAsync(() => api.beliefs(w!.group.key), [w?.group.key], { enabled: !!w });

  const byKey = useMemo(() => {
    const m = new Map<string, Belief[]>();
    // seed with the case file's beliefs so cards render even if history fails
    (w?.beliefs ?? []).forEach((b) => m.set(b.belief_key, [b]));
    if (hist.data) {
      const h = new Map<string, Belief[]>();
      hist.data.forEach((b) => {
        const arr = h.get(b.belief_key) ?? [];
        arr.push(b);
        h.set(b.belief_key, arr);
      });
      h.forEach((arr, k) => m.set(k, arr.sort((a, b) => a.version - b.version)));
    }
    return m;
  }, [w, hist.data]);

  if (!w) return <Empty title="No workplace beliefs in this case file" icon={<Users className="h-8 w-8" aria-hidden />} />;

  return (
    <>
      <Card title={<span>{w.group.employer} · {w.group.function} · {w.group.city}</span>} icon={<Users className="h-5 w-5 text-indigo-600 dark:text-indigo-400" aria-hidden />} subtitle={<>Group-level beliefs, never about one person. Group key <span className="font-mono">{w.group.key}</span></>}>
        <h3 className="mb-2 font-semibold">Joiners and leavers over time</h3>
        {w.timeline.length === 0 ? <Empty title="No timeline points" /> : <JoinLeaveChart data={w.timeline} />}
      </Card>

      <Card title="Beliefs" subtitle="Each belief keeps every version. Drag the slider to see how it changed.">
        {hist.loading && <Loading label="Loading belief history…" />}
        {!!hist.error && <ErrorState error={hist.error} onRetry={() => hist.reload()} />}
        {byKey.size === 0 ? (
          <Empty title="No beliefs for this group" />
        ) : (
          <div className="grid gap-4 lg:grid-cols-2">
            {[...byKey.entries()].map(([k, versions]) => (
              <BeliefCard key={k} versions={versions} />
            ))}
          </div>
        )}
      </Card>
    </>
  );
}

function JoinLeaveChart({ data }: { data: Timeline }) {
  const W = 760;
  const H = 280;
  const pad = { l: 44, r: 12, t: 16, b: 44 };
  const max = Math.max(1, ...data.map((d) => Math.max(d.joiners, d.leavers)));
  const step = niceStep(max);
  const top = Math.ceil(max / step) * step;
  const iw = W - pad.l - pad.r;
  const ih = H - pad.t - pad.b;
  const slot = iw / data.length;
  const bw = Math.max(4, Math.min(28, slot * 0.34));
  const y = (v: number) => pad.t + ih - (v / top) * ih;
  const ticks: number[] = [];
  for (let v = 0; v <= top; v += step) ticks.push(v);
  const labelEvery = Math.ceil(data.length / 10);
  return (
    <figure>
      <div className="mb-2 flex gap-4 text-sm" aria-hidden>
        <span className="flex items-center gap-1.5"><span className="h-3 w-3 rounded-sm bg-indigo-600 dark:bg-indigo-400" /> Joiners</span>
        <span className="flex items-center gap-1.5"><span className="h-3 w-3 rounded-sm bg-orange-500 dark:bg-orange-400" /> Leavers</span>
      </div>
      <svg viewBox={`0 0 ${W} ${H}`} className="h-auto w-full" role="img" aria-label={`Joiners and leavers across ${data.length} periods, peak ${max}`}>
        {ticks.map((t) => (
          <g key={t}>
            <line x1={pad.l} x2={W - pad.r} y1={y(t)} y2={y(t)} className="stroke-slate-200 dark:stroke-slate-800" />
            <text x={pad.l - 8} y={y(t)} textAnchor="end" dominantBaseline="middle" className="fill-slate-500 text-[12px] dark:fill-slate-400">
              {t}
            </text>
          </g>
        ))}
        {data.map((d, i) => {
          const cx0 = pad.l + slot * i + slot / 2;
          return (
            <g key={d.date}>
              <title>{`${fmtDate(d.date)}: ${d.joiners} joiners, ${d.leavers} leavers`}</title>
              <rect
                x={cx0 - bw - 1}
                y={y(d.joiners)}
                width={bw}
                height={Math.max(0, pad.t + ih - y(d.joiners))}
                rx={3}
                className="animate-grow-y fill-indigo-600 dark:fill-indigo-400"
                style={{ transformBox: "fill-box", transformOrigin: "bottom", animationDelay: `${i * 45}ms` }}
              />
              <rect
                x={cx0 + 1}
                y={y(d.leavers)}
                width={bw}
                height={Math.max(0, pad.t + ih - y(d.leavers))}
                rx={3}
                className="animate-grow-y fill-orange-500 dark:fill-orange-400"
                style={{ transformBox: "fill-box", transformOrigin: "bottom", animationDelay: `${i * 45 + 20}ms` }}
              />
              {i % labelEvery === 0 && (
                <text x={cx0} y={H - pad.b + 18} textAnchor="middle" className="fill-slate-600 text-[12px] dark:fill-slate-400">
                  {shortDate(d.date)}
                </text>
              )}
            </g>
          );
        })}
        <line x1={pad.l} x2={W - pad.r} y1={pad.t + ih} y2={pad.t + ih} className="stroke-slate-400 dark:stroke-slate-600" />
      </svg>
      <figcaption className="sr-only">
        <table>
          <thead>
            <tr><th>Date</th><th>Joiners</th><th>Leavers</th></tr>
          </thead>
          <tbody>
            {data.map((d) => (
              <tr key={d.date}><td>{d.date}</td><td>{d.joiners}</td><td>{d.leavers}</td></tr>
            ))}
          </tbody>
        </table>
      </figcaption>
    </figure>
  );
}

function niceStep(max: number) {
  const raw = max / 4;
  const p = Math.pow(10, Math.floor(Math.log10(raw || 1)));
  const n = raw / p;
  return (n <= 1 ? 1 : n <= 2 ? 2 : n <= 5 ? 5 : 10) * p;
}

function shortDate(s: string) {
  const d = new Date(s);
  if (isNaN(d.getTime())) return s;
  return d.toLocaleDateString(undefined, { month: "short", year: "2-digit", timeZone: "UTC" });
}

function BeliefCard({ versions }: { versions: Belief[] }) {
  const [idx, setIdx] = useState(versions.length - 1);
  useEffect(() => setIdx(versions.length - 1), [versions.length]);
  const b = versions[Math.min(idx, versions.length - 1)];
  const id = `slider-${b.belief_key}`;
  const numeric = versions.filter((v) => !v.suppressed && v.value !== null);
  return (
    <article className="flex flex-col rounded-xl border border-slate-200 p-4 dark:border-slate-700">
      <div className="flex items-start justify-between gap-2">
        <h4 className="font-semibold text-slate-900 dark:text-slate-100">{b.statement}</h4>
        <Badge tone={b.valid_to ? "slate" : "green"}>v{b.version}{b.valid_to ? "" : " · current"}</Badge>
      </div>
      <p className="font-mono text-sm text-slate-500 dark:text-slate-400">{b.belief_key}</p>

      {b.suppressed ? (
        <div className="my-3 flex items-start gap-3 rounded-lg border border-dashed border-slate-400 bg-slate-50 p-3 dark:border-slate-600 dark:bg-slate-800/60">
          <EyeOff className="mt-0.5 h-5 w-5 shrink-0 text-slate-500" aria-hidden />
          <div>
            <p className="font-semibold">Group too small</p>
            <p className="text-sm text-slate-600 dark:text-slate-400">
              Hidden to protect individuals (n = {b.n}).{b.reason ? ` ${b.reason}` : ""}
            </p>
          </div>
        </div>
      ) : (
        <p className="my-3 text-4xl font-semibold tabular-nums">
          {fmtNum(b.value, 2)}
          <span className="ml-2 text-base font-normal text-slate-500 dark:text-slate-400">n = {fmtNum(b.n)}</span>
        </p>
      )}

      <p className="text-sm text-slate-700 dark:text-slate-300">
        Valid {fmtDate(b.valid_from)} → {b.valid_to ? fmtDate(b.valid_to) : "now"}
      </p>

      {numeric.length > 1 && <Sparkline versions={versions} active={idx} />}

      {versions.length > 1 ? (
        <div className="mt-3">
          <label htmlFor={id} className="flex items-center gap-1.5 text-sm font-medium text-slate-700 dark:text-slate-300">
            <History className="h-4 w-4" aria-hidden /> Version {b.version} of {versions[versions.length - 1].version}
          </label>
          <input
            id={id}
            type="range"
            min={0}
            max={versions.length - 1}
            step={1}
            value={idx}
            onChange={(e) => setIdx(Number(e.target.value))}
            aria-valuetext={`Version ${b.version}, valid from ${b.valid_from}`}
            className="mt-1 w-full accent-indigo-600"
          />
        </div>
      ) : (
        <p className="mt-3 text-sm text-slate-500 dark:text-slate-400">Only one version so far.</p>
      )}
      <div className="mt-3">
        {b.sources.length > 0 ? (
          <SourceButton sources={b.sources} title={b.statement}>
            {b.sources.length} source{b.sources.length > 1 ? "s" : ""}
          </SourceButton>
        ) : (
          <span className="text-sm text-slate-500">No sources listed</span>
        )}
      </div>
    </article>
  );
}

function Sparkline({ versions, active }: { versions: Belief[]; active: number }) {
  const W = 240;
  const H = 44;
  const vals = versions.map((v) => (v.suppressed ? null : v.value));
  const nums = vals.filter((v): v is number => v !== null);
  const min = Math.min(...nums);
  const max = Math.max(...nums);
  const span = max - min || 1;
  const x = (i: number) => (versions.length === 1 ? W / 2 : 6 + (i / (versions.length - 1)) * (W - 12));
  const y = (v: number) => H - 6 - ((v - min) / span) * (H - 12);
  let d = "";
  vals.forEach((v, i) => {
    if (v === null) return;
    d += `${d ? "L" : "M"}${x(i)},${y(v)}`;
  });
  return (
    <svg viewBox={`0 0 ${W} ${H}`} className="mt-2 h-11 w-full max-w-[16rem]" aria-hidden>
      <path d={d} fill="none" strokeWidth={2} className="stroke-indigo-500" />
      {vals.map((v, i) =>
        v === null ? (
          <circle key={i} cx={x(i)} cy={H / 2} r={3} className="fill-none stroke-slate-400" strokeDasharray="2 2" />
        ) : (
          <circle key={i} cx={x(i)} cy={y(v)} r={i === active ? 5 : 3} className={i === active ? "fill-indigo-600 dark:fill-indigo-300" : "fill-slate-400"} />
        ),
      )}
    </svg>
  );
}
