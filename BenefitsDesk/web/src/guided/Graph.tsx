// The 3D neighbourhood graph, moved unchanged from the earlier Guided.tsx.
// Input: `cf` with `facts` and `peer_benchmark` (the dashboard's `graph_case`).
import { useEffect, useMemo, useRef } from "react";
import ForceGraph3D from "3d-force-graph";
import SpriteText from "three-spritetext";
import type { CaseFile } from "../types";
import type { Source } from "./api";

export type GraphCase = Pick<CaseFile, "facts" | "peer_benchmark">;

export const nice = (t: string) => t.replace(/(\d{4}-\d{2}-\d{2})T00:00:00\+00:00/g, "$1");

export function SourceRows({ s }: { s: Source | null | undefined }) {
  if (!s) return <p className="text-sm">No source: this is not a fact.</p>;
  const rows: [string, unknown][] = [["Record", s.record], ["Field", s.field_path], ["Passage", s.passage], ["Record date", s.record_date || "not given by the source"],
    ["Retrieved", s.retrieved_at], ["Link", s.url]];
  return (
    <dl className="space-y-2 text-sm">
      {rows.filter(([, v]) => v).map(([k, v]) => (
        <div key={k}><dt className="text-xs uppercase text-slate-500">{k}</dt>
          <dd className="break-words font-mono">{k === "Link" ? <a className="text-indigo-600 underline" href={String(v)} target="_blank" rel="noreferrer">{String(v)}</a> : String(v)}</dd></div>
      ))}
    </dl>
  );
}

type GNode = { id: string; label: string; kind: "you" | "employer" | "role" | "city" | "peers" | "phrase" | "rival"; title: string; body: React.ReactNode; val?: number; fx?: number; fy?: number; fz?: number };
type GLink = { source: string; target: string; illustrative?: boolean };
const COLORS: Record<string, string> = { you: "#6366f1", employer: "#10b981", role: "#0ea5e9", city: "#f59e0b", peers: "#ec4899", phrase: "#f472b6", rival: "#f43f5e" };

export function Graph({ cf, onPick, dark }: { cf: GraphCase; onPick: (t: string, b: React.ReactNode) => void; dark: boolean }) {
  const el = useRef<HTMLDivElement>(null);
  const data = useMemo(() => buildGraph(cf), [cf]);
  const pick = useRef(onPick); pick.current = onPick;
  useEffect(() => {
    const box = el.current;
    if (!box) return;
    const FG: any = ForceGraph3D;
    let g: any;
    try { g = new FG(box, { controlType: "orbit" }); } catch { g = FG({ controlType: "orbit" })(box); }
    const ink = dark ? "#e2e8f0" : "#0f172a";
    g.width(box.clientWidth).height(480).backgroundColor(dark ? "#0b1120" : "#f8fafc").showNavInfo(false)
      .graphData({ nodes: data.nodes.map((n) => ({ ...n })), links: data.links.map((l) => ({ ...l })) })
      .cooldownTicks(0).warmupTicks(0)                       // fixed layout: no simulation, no lag
      .nodeColor((n: GNode) => COLORS[n.kind]).nodeVal((n: GNode) => n.val || 4).nodeResolution(16).nodeOpacity(1)
      .nodeLabel((n: GNode) => n.title)
      .nodeThreeObjectExtend(true)
      .nodeThreeObject((n: GNode) => {
        const t = new (SpriteText as any)(n.label);
        t.color = ink; t.textHeight = n.kind === "you" ? 7 : 4.2; t.fontWeight = n.kind === "you" ? "700" : "500";
        t.backgroundColor = dark ? "rgba(11,17,32,0.75)" : "rgba(248,250,252,0.8)"; t.padding = 1.5; t.borderRadius = 3;
        t.position.y = -(Math.cbrt(n.val || 4) * 4 + 6);
        return t;
      })
      .linkColor((l: GLink) => (l.illustrative ? "#94a3b8" : COLORS.you)).linkOpacity(0.6)
      .linkWidth((l: GLink) => (l.illustrative ? 0 : 1.2))
      .linkDirectionalParticles((l: GLink) => (l.illustrative ? 0 : 2)).linkDirectionalParticleWidth(1.6).linkDirectionalParticleSpeed(0.006)
      .linkLabel((l: GLink) => (l.illustrative ? "illustrative link: not from data" : "from a record"))
      .onNodeClick((n: any) => {
        pick.current(n.title, n.body);
        const d = 90, r = 1 + d / Math.hypot(n.x || 1, n.y || 1, n.z || 1);
        g.cameraPosition({ x: (n.x || 0) * r, y: (n.y || 0) * r, z: (n.z || 0) * r + 40 }, n, 900);
      })
      .cameraPosition({ x: 0, y: 30, z: 300 });
    const ctl = g.controls(); if (ctl) { ctl.autoRotate = true; ctl.autoRotateSpeed = 0.35; ctl.enableDamping = true; }
    // render only while visible
    const io = new IntersectionObserver(([e]) => (e.isIntersecting ? g.resumeAnimation() : g.pauseAnimation()));
    io.observe(box);
    const onResize = () => g.width(box.clientWidth);
    window.addEventListener("resize", onResize);
    return () => { io.disconnect(); window.removeEventListener("resize", onResize); g.pauseAnimation(); g._destructor?.(); box.innerHTML = ""; };
  }, [data, dark]);
  return (
    <div className="grid gap-4 lg:grid-cols-[1fr_220px]">
      <div>
        <div ref={el} className="overflow-hidden rounded-xl border border-slate-200 dark:border-slate-800" aria-label="3D map of the groups around you" />
        <p className="mt-2 text-xs text-slate-500 dark:text-slate-400">Drag to rotate · scroll to zoom · click a node to open its card. Moving dots run along links that come from records; the faint link is illustrative.</p>
      </div>
      <ul className="space-y-1.5 text-sm" aria-label="Nodes (keyboard access)">
        {data.nodes.map((n) => (
          <li key={n.id}><button onClick={() => onPick(n.title, n.body)} className="flex w-full items-center gap-2 rounded-md border border-slate-200 px-2 py-1.5 text-left hover:bg-slate-100 focus:outline-none focus:ring-2 focus:ring-indigo-500 dark:border-slate-700 dark:hover:bg-slate-800">
            <span className="h-3 w-3 shrink-0 rounded-full" style={{ background: COLORS[n.kind] }} /><span className="truncate">{n.label}</span></button></li>
        ))}
      </ul>
    </div>
  );
}

function ring(nodes: GNode[], radius: number, cx: number, phase = 0) {
  nodes.forEach((n, i) => { const t = phase + (2 * Math.PI * i) / Math.max(nodes.length, 1); n.fx = cx + radius * Math.cos(t); n.fy = radius * Math.sin(t); n.fz = 15 * Math.sin(2 * t); });
}

function buildGraph(cf: GraphCase): { nodes: GNode[]; links: GLink[] } {
  const by = Object.fromEntries((cf.facts || []).map((f) => [f.fact_id, f]));
  const nodes: GNode[] = [], links: GLink[] = [];
  const cv = (t: string) => <div className="rounded bg-amber-100 p-2 text-amber-900">Cannot verify: {t}</div>;
  nodes.push({ id: "you", label: "You", kind: "you", val: 14, fx: -85, fy: 0, fz: 0, title: "You",
    body: <p className="text-sm">The person at the centre. Only facts you told us, or a record states, are used. Nobody else is shown by name.</p> });
  const mine: GNode[] = [];
  const emp = by.current_employer?.value ? by.current_employer : by.last_past_employer;
  if (emp?.value) mine.push({ id: "employer", label: `Employer · ${emp.value}`, kind: "employer", val: 8, title: `${emp.value} (employer group)`,
    body: <div className="space-y-3 text-sm"><p>{nice(emp.statement)}</p><SourceRows s={emp.source} />{cv("workplace numbers (joiners, leavers, group size) were not computed for this group.")}</div> });
  const title = by.current_title?.value ? by.current_title : by.last_past_title;
  if (title?.value) mine.push({ id: "role", label: `Role · ${title.value}`, kind: "role", val: 6, title: `${title.value} (role group)`,
    body: <div className="space-y-3 text-sm"><p>{nice(title.statement)}</p><SourceRows s={title.source} />{cv("no group size for this role group.")}</div> });
  if (by.city?.value) mine.push({ id: "city", label: `City · ${by.city.value}`, kind: "city", val: 6, title: `${by.city.value} (city group)`,
    body: <div className="space-y-3 text-sm"><p>You told us you live here.</p><SourceRows s={by.city.source} />{cv("no group data for this city.")}</div> });
  ring(mine, 55, -85, Math.PI / 2);
  mine.forEach((n) => { nodes.push(n); links.push({ source: "you", target: n.id }); });
  if (mine.some((n) => n.id === "role") && mine.some((n) => n.id === "employer")) links.push({ source: "role", target: "employer" });

  const pb = cf.peer_benchmark;
  if (pb && pb.total != null) {
    const src = pb.source;
    nodes.push({ id: "peers", label: `Logistics employers · ${pb.total.toLocaleString("en-IN")} posts`, kind: "peers", val: 10, fx: 85, fy: 0, fz: 0,
      title: "Peer group: logistics employers in India",
      body: <div className="space-y-3 text-sm">
        <div className="text-3xl font-bold">{pb.any_cover.count ?? "—"} <span className="text-base font-normal">of {pb.total.toLocaleString("en-IN")} job posts</span></div>
        <p>mention any cover phrase ({pb.any_cover.share != null ? (pb.any_cover.share * 100).toFixed(1) + "%" : "cannot verify"}) since {(pb as any).since}. Group size: {pb.total.toLocaleString("en-IN")} posts.</p>
        <p className="text-slate-500">{pb.note}</p><SourceRows s={src} />
        <details><summary className="cursor-pointer">Filter used</summary><pre className="overflow-auto text-xs">{JSON.stringify(pb.filter, null, 1)}</pre></details></div> });
    links.push({ source: "you", target: "peers", illustrative: true });
    const kids: GNode[] = [];
    for (const ph of pb.phrases.filter((x) => x.count)) {
      kids.push({ id: `ph-${ph.phrase}`, label: `"${ph.phrase}" · ${ph.count}`, kind: "phrase", val: 2 + Math.log2(1 + (ph.count || 0)), title: `Posts mentioning "${ph.phrase}"`,
        body: <div className="space-y-3 text-sm"><div className="text-3xl font-bold">{ph.count} <span className="text-base font-normal">of {pb.total.toLocaleString("en-IN")} posts</span></div>
          <p>({ph.share != null ? (ph.share * 100).toFixed(1) + "%" : "—"}) contain the exact phrase “{ph.phrase}”.</p><SourceRows s={src} /></div> });
    }
    for (const sm of pb.samples || []) {
      kids.push({ id: `rival-${sm.job_id}`, label: `Rival · ${sm.company}`, kind: "rival", val: 4, title: `${sm.company} (employer in the peer group)`,
        body: <div className="space-y-3 text-sm"><p>One job post from this employer mentions “{sm.phrase}”.</p><blockquote className="border-l-4 pl-3 italic">…{sm.passage}…</blockquote>
          <SourceRows s={{ record: "crustdata /job/search", field_path: "content.description", url: sm.url, record_date: sm.date_added, retrieved_at: (sm as any).retrieved_at || src.retrieved_at }} />
          <p className="text-slate-500">One post is not the employer's whole benefits policy.</p></div> });
    }
    ring(kids, 62, 85, 0.3);
    kids.forEach((k) => { nodes.push(k); links.push({ source: "peers", target: k.id }); });
  }
  return { nodes, links };
}
