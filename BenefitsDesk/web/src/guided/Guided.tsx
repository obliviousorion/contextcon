import { useEffect, useMemo, useRef, useState } from "react";
import ForceGraph3D from "3d-force-graph";
import SpriteText from "three-spritetext";
import type { CaseFile, Fact, Source } from "../types";

// The consenting demo persona (requests/L1_persona_a_review.json). Never the under-18 refusal case.
const PERSONA_URL = "https://www.linkedin.com/in/atishayjain2510/";
const INSURERS = ["Star Health and Allied Insurance", "Niva Bupa Health Insurance", "Care Health Insurance"];

type Q = { key: string; ask: string; chips: { label: string; value: unknown }[]; multi?: boolean; free?: boolean };
const QUESTIONS: Q[] = [
  { key: "want", ask: "Hi! I'm the Benefits Desk. What cover are you looking for?",
    chips: [{ label: "Health cover", value: "health" }, { label: "Life cover for my family", value: "life" },
            { label: "Accident cover", value: "accident" }, { label: "Not sure, check everything", value: "all" }] },
  { key: "age_band", ask: "Which age band are you in?",
    chips: ["18-24", "25-34", "35-44", "45-54", "55-64", "65+"].map((v) => ({ label: v, value: v })) },
  { key: "dependants", ask: "How many people depend on your income?",
    chips: [0, 1, 2, 3, 4].map((v) => ({ label: v === 4 ? "4 or more" : String(v), value: v })) },
  { key: "city", ask: "Which city do you live in?", free: true,
    chips: ["Pilani", "Jaipur", "Gurugram", "Bengaluru", "Mumbai"].map((v) => ({ label: v, value: v })) },
  { key: "cover_held", ask: "Which cover do you already have? Pick all that apply, then Done.", multi: true,
    chips: [{ label: "Employer group health", value: "employer_group_health" }, { label: "Personal health", value: "personal_health" },
            { label: "Term life", value: "term_life" }, { label: "Personal accident", value: "personal_accident" }] },
  { key: "monthly_budget_inr", ask: "Roughly how much could you spend on cover each month?",
    chips: [300, 600, 1000, 2000, 5000].map((v) => ({ label: `₹${v.toLocaleString("en-IN")}`, value: v })) },
  { key: "chosen_insurer", ask: "Regulator figures for insurers can't be verified right now, so I won't rank them. Which insurer should I prepare the application for?",
    chips: INSURERS.map((v) => ({ label: v, value: v })) },
];

type Msg = { from: "agent" | "you"; text: string };

async function j<T>(url: string, body?: unknown): Promise<T> {
  const r = await fetch(url, body === undefined ? undefined : { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify(body) });
  if (!r.ok && r.status >= 500) throw new Error(`HTTP ${r.status}`);
  return r.json();
}

const STEPS = ["Chat", "Profile", "Neighbourhood", "What you're missing", "Next step"];

export default function Guided() {
  const [msgs, setMsgs] = useState<Msg[]>([{ from: "agent", text: QUESTIONS[0].ask }]);
  const [qi, setQi] = useState(0);
  const [answers, setAnswers] = useState<Record<string, unknown>>({});
  const [multi, setMulti] = useState<string[]>([]);
  const [free, setFree] = useState("");
  const [runId, setRunId] = useState<string | null>(null);
  const [cf, setCf] = useState<CaseFile | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [shown, setShown] = useState(0);
  const [open, setOpen] = useState<{ title: string; body: React.ReactNode } | null>(null);
  const [live, setLive] = useState<string[]>([]);
  useEffect(() => {
    if (!runId) return;
    const es = new EventSource(`/api/stream?run_id=${runId}`);
    const words: Record<string, string> = { sign_up: "Consent and sign-up recorded", person_record: "Public work record read", alarm: "Job-change rule checked",
      peer_benchmark: "Similar employers' job posts counted", gaps: "Rules file applied", shortlist: "Insurer figures checked", prepare_application: "Application pre-filled (not sent)" };
    es.onmessage = (m) => { const e = JSON.parse(m.data); if (e.status === "done" && words[e.step]) setLive((x) => (x.includes(words[e.step]) ? x : [...x, words[e.step]])); if (e.status === "finished") es.close(); };
    return () => es.close();
  }, [runId]);
  // bring each new step into view
  const stage = !runId ? 1 : !cf ? 2 : shown < factsOf(cf).length ? 2 : 3;
  useEffect(() => { if (stage > 1) document.getElementById(`s${stage}`)?.scrollIntoView({ behavior: "smooth", block: "start" }); }, [stage]);
  const [dark, setDark] = useState(() => window.matchMedia?.("(prefers-color-scheme: dark)").matches);

  useEffect(() => { document.documentElement.classList.toggle("dark", !!dark); }, [dark]);

  const step = !runId ? 1 : !cf ? 2 : shown < factsOf(cf).length ? 2 : 5;

  function answer(q: Q, label: string, value: unknown) {
    const next = { ...answers, [q.key]: value };
    setAnswers(next);
    const m: Msg[] = [...msgs, { from: "you", text: label }];
    if (qi + 1 < QUESTIONS.length) {
      m.push({ from: "agent", text: QUESTIONS[qi + 1].ask });
      setQi(qi + 1);
    } else {
      m.push({ from: "agent", text: "Thanks. I'm checking your public work record and similar employers' job posts now. Every fact will show where it came from." });
      start(next);
      setQi(qi + 1);
    }
    setMsgs(m);
    setMulti([]); setFree("");
  }

  async function start(a: Record<string, unknown>) {
    const { want, ...facts } = a;
    const request = { id: "G1", type: "employee_review", said: `I want ${String(want)} cover. What do I have, what's missing, what should I do?`,
      persona: { profile_url: PERSONA_URL, consent: true, answers: facts }, since: "2026-09-01", as_of: "2026-11-22" };
    try {
      const r = await j<{ run_id: string }>("/api/run", { request });
      setRunId(r.run_id);
    } catch (e) { setErr(`Could not start the run: ${e}. Is the backend running (uv run python -m bd serve)?`); }
  }

  // poll the case file until the run finishes
  useEffect(() => {
    if (!runId || cf) return;
    const t = setInterval(async () => {
      try {
        const c = await j<any>(`/api/runs/${runId}`);
        if (c.status !== "running" && "facts" in c) { setCf(c); clearInterval(t); }
        else if (c.status === "stopped") { setErr("The run stopped. Open Behind the scenes to resume it."); clearInterval(t); }
      } catch { /* keep polling */ }
    }, 800);
    return () => clearInterval(t);
  }, [runId, cf]);

  // facts appear one by one
  useEffect(() => {
    if (!cf) return;
    const n = factsOf(cf).length;
    if (shown >= n) return;
    const t = setTimeout(() => setShown(shown + 1), 280);
    return () => clearTimeout(t);
  }, [cf, shown]);

  const q = QUESTIONS[qi];
  return (
    <div className="min-h-screen bg-slate-50 text-slate-900 dark:bg-slate-950 dark:text-slate-100">
      <header className="sticky top-0 z-20 scroll-mt-0 border-b border-slate-200 bg-white dark:border-slate-800 dark:bg-slate-900">
        <div className="mx-auto flex max-w-5xl flex-wrap items-center gap-4 px-4 py-3">
          <div className="mr-auto">
            <div className="text-lg font-bold">Benefits Desk</div>
            <div className="text-xs text-slate-500 dark:text-slate-400">A tool for a licensed broker. Nothing is bought or sent without your approval.</div>
          </div>
          {qi > 0 && <button className="rounded-md border px-3 py-1.5 text-sm dark:border-slate-700" onClick={() => window.location.reload()}>Start over</button>}
          <button className="rounded-md border px-3 py-1.5 text-sm dark:border-slate-700" onClick={() => setDark(!dark)}>{dark ? "Light" : "Dark"} theme</button>
          <a className="rounded-md border border-indigo-300 px-3 py-1.5 text-sm text-indigo-700 dark:border-indigo-700 dark:text-indigo-300"
             href={`/console${runId ? `#/console/${runId}` : ""}`}>Behind the scenes ↗</a>
        </div>
        <ol className="mx-auto flex max-w-5xl gap-1 px-4 pb-3" aria-label="Progress">
          {STEPS.map((s, i) => {
            const n = i + 1, done = n < step || (cf && n <= 5), cur = n === step;
            return (
              <li key={s} className={`flex flex-1 items-center gap-2 rounded-md px-2 py-1 text-xs sm:text-sm ${cur ? "bg-indigo-600 text-white" : done ? "bg-indigo-100 text-indigo-800 dark:bg-indigo-900/50 dark:text-indigo-200" : "bg-slate-100 text-slate-500 dark:bg-slate-800"}`}>
                <span className="font-bold">{n}</span><span className="truncate">{s}</span>
              </li>
            );
          })}
        </ol>
      </header>

      <main className="mx-auto max-w-5xl space-y-6 px-4 py-6">
        {err && <div role="alert" className="rounded-lg border border-red-300 bg-red-50 p-3 text-red-800 dark:border-red-800 dark:bg-red-950 dark:text-red-200">{err}</div>}

        <Section n={1} title="Chat">
          <div className="space-y-2" aria-live="polite">
            {msgs.map((m, i) => (
              <div key={i} className={`flex ${m.from === "you" ? "justify-end" : ""}`}>
                <div className={`max-w-[80%] rounded-2xl px-4 py-2 ${m.from === "you" ? "bg-indigo-600 text-white" : "bg-white shadow-sm dark:bg-slate-800"}`}>{m.text}</div>
              </div>
            ))}
          </div>
          {q && (
            <div className="mt-4 flex flex-wrap gap-2">
              {q.chips.map((c) => {
                const on = q.multi && multi.includes(String(c.value));
                return (
                  <button key={c.label} onClick={() => q.multi ? setMulti(on ? multi.filter((x) => x !== c.value) : [...multi, String(c.value)]) : answer(q, c.label, c.value)}
                    className={`rounded-full border px-4 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 ${on ? "border-indigo-600 bg-indigo-600 text-white" : "border-indigo-300 bg-white hover:bg-indigo-50 dark:border-indigo-700 dark:bg-slate-900 dark:hover:bg-slate-800"}`}>
                    {c.label}
                  </button>
                );
              })}
              {q.multi && (
                <button onClick={() => answer(q, multi.length ? multi.map((v) => q.chips.find((c) => c.value === v)?.label).join(", ") : "None", multi)}
                  className="rounded-full bg-indigo-600 px-4 py-2 text-sm font-semibold text-white">{multi.length ? "Done" : "I have none"}</button>
              )}
              {q.free && (
                <form onSubmit={(e) => { e.preventDefault(); if (free.trim()) answer(q, free.trim(), free.trim()); }} className="flex gap-2">
                  <input aria-label="Type your city" value={free} onChange={(e) => setFree(e.target.value)} placeholder="or type it"
                    className="rounded-full border px-4 py-2 text-sm dark:border-slate-700 dark:bg-slate-900" />
                </form>
              )}
            </div>
          )}
        </Section>

        {runId && (
          <Section n={2} title="Your profile builds">
            {!cf ? (
              <div className="space-y-2"><Spinner text="Working on it. Each line below is a real step finishing on the server." />
                <ul className="ml-1 space-y-1 text-sm">{live.map((w) => <li key={w} className="animate-[fadein_.3s_ease-out]">✓ {w}</li>)}</ul></div>
            ) : (
              <>
                <p className="mb-3 text-sm text-slate-500 dark:text-slate-400">Each chip says how we know it. Click one to see the exact source field and its date.</p>
                <div className="flex flex-wrap gap-2">
                  {factsOf(cf).slice(0, shown).map((f) => (
                    <button key={f.fact_id} onClick={() => setOpen({ title: f.statement, body: <SourceBox f={f} /> })}
                      className={`animate-[fadein_.3s_ease-out] rounded-lg border px-3 py-2 text-left text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 ${f.label === "told" ? "border-sky-300 bg-sky-50 dark:border-sky-800 dark:bg-sky-950" : "border-emerald-300 bg-emerald-50 dark:border-emerald-800 dark:bg-emerald-950"}`}>
                      <span className="mr-2 text-[10px] font-bold uppercase tracking-wide">{f.label === "told" ? "Told" : "Checked"}</span>
                      {nice(f.statement)}{(f as Fact & { cannot_verify?: boolean }).cannot_verify && <span className="ml-2 rounded bg-amber-200 px-1 text-[10px] font-bold text-amber-900">CANNOT VERIFY</span>}
                    </button>
                  ))}
                </div>
                {(cf.questions || []).length > 0 && shown >= factsOf(cf).length && (
                  <div className="mt-4 rounded-lg border border-amber-300 bg-amber-50 p-3 text-sm dark:border-amber-800 dark:bg-amber-950">
                    <div className="font-semibold">I need to ask you</div>
                    <ul className="ml-5 list-disc">{cf.questions!.map((x, i) => <li key={i}>{x.question} <span className="text-slate-500">({x.why})</span></li>)}</ul>
                  </div>
                )}
              </>
            )}
          </Section>
        )}

        {cf && shown >= factsOf(cf).length && (
          <>
            <Section n={3} title="Your neighbourhood (groups only, never individuals)">
              <Graph cf={cf} onPick={(title, body) => setOpen({ title, body })} dark={!!dark} />
            </Section>
            <Section n={4} title="What you're missing">
              {(cf.gaps || []).length === 0 ? <p>No rule in the rules file fired for your answers.</p> : (
                <ul className="divide-y divide-dashed divide-slate-300 rounded-lg border bg-white font-mono text-sm dark:divide-slate-700 dark:border-slate-700 dark:bg-slate-900">
                  {cf.gaps!.map((g) => (
                    <li key={g.rule_id} className="p-3">
                      <span className="mr-2 rounded bg-slate-200 px-1.5 py-0.5 text-xs font-bold dark:bg-slate-700">{g.rule_id}</span>
                      <span className={`mr-2 text-xs font-bold uppercase ${g.severity === "high" ? "text-red-600" : g.severity === "medium" ? "text-amber-600" : "text-slate-500"}`}>{g.severity}</span>
                      {g.explanation} → <b>{g.called_for}</b>
                      <div className="mt-1 text-xs text-slate-500">facts used: {g.facts_used.join(", ")}</div>
                    </li>
                  ))}
                </ul>
              )}
              {(cf.cannot_verify || []).length > 0 && (
                <details className="mt-3 text-sm"><summary className="cursor-pointer font-semibold text-amber-700 dark:text-amber-300">Cannot verify ({cf.cannot_verify!.length})</summary>
                  <ul className="ml-5 mt-1 list-disc">{cf.cannot_verify!.map((c, i) => <li key={i}>{c.statement}: missing {c.missing}</li>)}</ul></details>
              )}
            </Section>
            <Section n={5} title="Next step">
              <NextStep cf={cf} />
            </Section>
          </>
        )}
      </main>

      {open && (
        <div role="dialog" aria-modal className="fixed inset-0 z-30 flex justify-end bg-black/40" onClick={() => setOpen(null)}>
          <div className="h-full w-full max-w-md overflow-auto bg-white p-5 shadow-xl dark:bg-slate-900" onClick={(e) => e.stopPropagation()}>
            <div className="mb-3 flex items-start gap-3"><h3 className="mr-auto text-lg font-semibold">{open.title}</h3>
              <button autoFocus className="rounded border px-2 dark:border-slate-700" onClick={() => setOpen(null)}>Close</button></div>
            {open.body}
          </div>
        </div>
      )}
      <style>{`@keyframes fadein{from{opacity:0;transform:translateY(6px)}to{opacity:1;transform:none}}`}</style>
    </div>
  );
}

const nice = (t: string) => t.replace(/(\d{4}-\d{2}-\d{2})T00:00:00\+00:00/g, "$1");

function factsOf(cf: CaseFile): Fact[] {
  return (cf.facts || []).filter((f) => f.label === "told" || f.label === "checked");
}

function Section({ n, title, children }: { n: number; title: string; children: React.ReactNode }) {
  return (
    <section aria-labelledby={`s${n}`} className="scroll-mt-32 rounded-2xl border border-slate-200 bg-white/60 p-5 shadow-sm dark:border-slate-800 dark:bg-slate-900/60">
      <h2 id={`s${n}`} className="mb-4 flex items-center gap-3 text-lg font-semibold">
        <span className="flex h-7 w-7 items-center justify-center rounded-full bg-indigo-600 text-sm text-white">{n}</span>{title}
      </h2>
      {children}
    </section>
  );
}

function Spinner({ text }: { text: string }) {
  return <div className="flex items-center gap-3 text-slate-500" role="status"><span className="h-4 w-4 animate-spin rounded-full border-2 border-indigo-500 border-t-transparent" />{text}</div>;
}

function SourceRows({ s }: { s: Source | null | undefined }) {
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

function SourceBox({ f }: { f: Fact }) {
  const x = f as Fact & { cannot_verify?: boolean; missing?: string };
  return (
    <div className="space-y-3">
      <div className="text-sm"><b>{f.label === "told" ? "Told" : "Checked"}</b>: {f.label === "told" ? "you said this." : "a record states this."}</div>
      {x.cannot_verify && <div className="rounded bg-amber-100 p-2 text-sm text-amber-900">Cannot verify: missing {x.missing}</div>}
      <SourceRows s={f.source} />
    </div>
  );
}

type GNode = { id: string; label: string; kind: "you" | "employer" | "role" | "city" | "peers" | "phrase" | "rival"; title: string; body: React.ReactNode; val?: number; fx?: number; fy?: number; fz?: number };
type GLink = { source: string; target: string; illustrative?: boolean };
const COLORS: Record<string, string> = { you: "#6366f1", employer: "#10b981", role: "#0ea5e9", city: "#f59e0b", peers: "#ec4899", phrase: "#f472b6", rival: "#f43f5e" };

function Graph({ cf, onPick, dark }: { cf: CaseFile; onPick: (t: string, b: React.ReactNode) => void; dark: boolean }) {
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

function buildGraph(cf: CaseFile): { nodes: GNode[]; links: GLink[] } {
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

function NextStep({ cf }: { cf: CaseFile }) {
  const [acts, setActs] = useState(cf.actions || []);
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState<string | null>(null);
  const [count, setCount] = useState<number | null>(null);
  const a = acts.find((x) => x.action === "submit_application") || acts[0];

  async function refresh() {
    const all = await j<any[]>("/api/approvals");
    const mine = all.filter((x) => acts.some((y) => y.key === x.key));
    if (mine.length) setActs(mine);
    try {
      const sb = await j<any[]>("/api/sandbox");
      const r = Array.isArray(sb) ? sb.find((x) => x.key === a?.key) : null;
      setCount(r ? r.count : 0);
    } catch { setCount(null); }
  }
  useEffect(() => { refresh(); const t = setInterval(refresh, 1500); return () => clearInterval(t); }, [a?.key]);

  if (!a) return <p>No action was prepared. {(cf.questions || []).length ? "Answer the questions above first." : "No gap called for one."}</p>;
  async function approve() {
    setBusy(true);
    try {
      const r = await j<{ approved: boolean; already: boolean }>("/api/approve", { key: a.key, approver: "person" });
      setMsg(r.already ? "Already approved: it will still be sent only once." : "Approved. Sending to the sandbox once…");
      await j("/api/act", { run_id: a.run_id });
      setTimeout(refresh, 1200);
    } finally { setBusy(false); }
  }
  const done = a.status === "done";
  return (
    <div className="space-y-3">
      <div className="rounded-lg border bg-white p-4 dark:border-slate-700 dark:bg-slate-900">
        <div className="font-semibold">{a.summary}</div>
        <div className="mt-1 text-sm text-slate-500">Can it be undone? <b>{a.reversible ? "Yes" : "No"}</b> · {a.cost_note}</div>
        <div className="mt-1 text-sm">Status: <b>{a.status.replace("_", " ")}</b>{a.approved_by ? ` · approved by ${a.approved_by}` : ""}</div>
      </div>
      <button disabled={busy || done} onClick={approve}
        className="rounded-lg bg-emerald-600 px-5 py-2.5 font-semibold text-white focus:outline-none focus:ring-2 focus:ring-emerald-400 disabled:opacity-60">
        {done ? "Sent" : "Approve and send"}
      </button>
      {done && !msg && <p className="text-sm">This exact application was already sent{a.done_at ? ` at ${a.done_at}` : ""}. The same answers make the same action key, so it is never sent twice.</p>}
      {msg && <p className="text-sm">{msg}</p>}
      <p className={`text-sm font-semibold ${count === 1 ? "text-emerald-600" : count && count > 1 ? "text-red-600" : "text-slate-500"}`}>
        Sandbox receipts for this action: {count == null ? "sandbox not reachable" : count === 0 ? "none yet" : count === 1 ? "1 (exactly once)" : `${count} (DUPLICATE)`}
      </p>
    </div>
  );
}
