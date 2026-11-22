/* eslint-disable @typescript-eslint/no-explicit-any */
import { Fragment, useCallback, useEffect, useMemo, useRef, useState } from "react";
import { api, errText, type Dashboard as Dash, type DiaryEntry, type Fact, type Insurer, type Mode, type TrailStep } from "./api";
import { Graph, nice, type GraphCase } from "./Graph";
import { Button, CannotVerify, Empty, ErrorText, LabelTag, Loading, Tag, Tile, day, line, muted, sourcePanel, type Panel } from "./ui";

type Props = { dark: boolean; openPanel: (p: Panel) => void; onLoggedOut: () => void };

const STEP_ORDER: { key: TrailStep["key"]; title: string }[] = [
  { key: "you", title: "You" }, { key: "employer", title: "Your employer" }, { key: "people", title: "People like you" },
  { key: "insurers", title: "Insurers" }, { key: "gaps", title: "Gaps" },
];

export default function Dashboard({ dark, openPanel, onLoggedOut }: Props) {
  const [dash, setDash] = useState<Dash | null>(null);
  const [viewDate, setViewDate] = useState<string | null>(null);   // null = today
  const [slider, setSlider] = useState<number | null>(null);
  const [err, setErr] = useState("");
  const [busy, setBusy] = useState("");
  const seq = useRef(0);

  const load = useCallback(async (asOf: string | null) => {
    const n = ++seq.current;
    try {
      const d = await api<Dash>(`/api/dashboard${asOf ? `?as_of=${encodeURIComponent(asOf)}` : ""}`);
      if (n === seq.current) { setDash(d); setErr(""); }
    } catch (e: any) {
      if (e?.status === 401) { onLoggedOut(); return; }
      if (n === seq.current) setErr(errText(e));
    }
  }, [onLoggedOut]);

  useEffect(() => { load(viewDate); }, [viewDate, load]);

  // poll while a run is going
  const running = dash?.run.status === "running";
  useEffect(() => {
    if (!running) return;
    const t = setTimeout(() => load(viewDate), 1500);
    return () => clearTimeout(t);
  }, [running, dash, viewDate, load]);

  // slider: move freely, fetch shortly after it stops
  useEffect(() => {
    if (slider == null || !dash) return;
    const d = dash.dates[slider];
    const t = setTimeout(() => setViewDate(slider === dash.dates.length - 1 ? null : d), 250);
    return () => clearTimeout(t);
  }, [slider]); // eslint-disable-line react-hooks/exhaustive-deps

  async function run(label: string, f: () => Promise<void>) {
    setBusy(label); setErr("");
    try { await f(); } catch (e: any) { if (e?.status === 401) onLoggedOut(); else setErr(errText(e)); } finally { setBusy(""); }
  }
  const check = () => run("check", async () => { await api("/api/check", {}); setSlider(null); setViewDate(null); await load(null); });
  const setMode = (mode: Mode) => run("mode", async () => {
    const r = await api<{ mode: Mode }>("/api/mode", { mode });
    setDash((d) => (d ? { ...d, user: { ...d.user, mode: r.mode } } : d));
  });

  // stable graph input, so polling does not rebuild the 3D scene unless the data changed
  const gKey = dash ? JSON.stringify(dash.graph_case) : "";
  const graphCase = useMemo(() => (dash ? (dash.graph_case as unknown as GraphCase) : null), [gKey]); // eslint-disable-line react-hooks/exhaustive-deps

  if (!dash) {
    return (
      <div className="py-10">
        {err ? <div className="space-y-3"><ErrorText>{err}</ErrorText><Button onClick={() => load(viewDate)}>Try again</Button></div>
          : <Loading text="Loading your dashboard" />}
      </div>
    );
  }

  const dates = dash.dates || [];
  const idx = slider ?? (viewDate ? Math.max(0, dates.indexOf(viewDate)) : dates.length - 1);
  const past = viewDate != null;

  return (
    <div className="space-y-6 py-6">
      {/* controls */}
      <div className={`grid gap-6 rounded-lg border ${line} p-5 lg:grid-cols-[1fr_auto]`}>
        <div className="min-w-0">
          <label htmlFor="asof" className="block text-sm font-medium">
            Showing what we believed on <span className="tabular-nums">{day(dash.as_of)}</span>{past ? "" : " (today)"}
          </label>
          {dates.length > 1 ? (
            <div className="mt-3 flex items-center gap-3">
              <span className={`text-xs tabular-nums ${muted}`}>{day(dates[0])}</span>
              <input id="asof" type="range" min={0} max={dates.length - 1} step={1} value={idx}
                aria-valuetext={day(dates[idx])} onChange={(e) => setSlider(Number(e.target.value))}
                className="min-w-0 flex-1 accent-blue-600" />
              <span className={`text-xs tabular-nums ${muted}`}>{day(dates[dates.length - 1])}</span>
              <Button disabled={!past && slider == null} onClick={() => { setSlider(null); setViewDate(null); }}>Today</Button>
            </div>
          ) : <p className={`mt-2 text-sm ${muted}`}>Only one date so far. Earlier views appear after the next check.</p>}
          <p className={`mt-3 text-sm ${muted}`}>
            {dash.user.last_checked ? <>Last checked {day(dash.user.last_checked)}. </> : "Not checked yet. "}
            Cost so far: {dash.cost.credits} credits (₹{dash.cost.inr}).
          </p>
        </div>
        <div className="flex flex-col gap-3 lg:items-end">
          <div className="flex items-center gap-3">
            <span id="mode-l" className="text-sm font-medium">Data</span>
            <div role="group" aria-labelledby="mode-l" className={`inline-flex rounded-lg border ${line} p-0.5`}>
              {(["live", "replay"] as Mode[]).map((m) => (
                <button key={m} type="button" aria-pressed={dash.user.mode === m} disabled={busy === "mode"} onClick={() => dash.user.mode !== m && setMode(m)}
                  className={`rounded-md px-3 py-1.5 text-sm ${dash.user.mode === m ? "bg-blue-600 text-white" : "text-neutral-600 dark:text-neutral-300"}`}>
                  {m === "live" ? "Live" : "Replay"}
                </button>
              ))}
            </div>
          </div>
          <p className={`text-xs ${muted}`}>{dash.user.mode === "live" ? "Next run uses live Crustdata calls" : "Next run replays recorded responses"}</p>
          <Button kind="primary" disabled={running || busy === "check"} onClick={check}>
            {running ? "Checking…" : busy === "check" ? "Starting…" : "Check for changes"}
          </Button>
        </div>
      </div>

      <RunBanner status={dash.run.status} />
      <ErrorText>{err}</ErrorText>

      {/* bento grid */}
      <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-6 lg:grid-flow-row-dense">
        <Tile title="Your neighbourhood" className="gd-graph md:col-span-2 lg:col-span-4 lg:row-span-2">
          {graphCase && ((graphCase.facts || []).length || graphCase.peer_benchmark)
            ? <Graph cf={graphCase} onPick={(title, body) => openPanel({ title, body })} dark={dark} />
            : running ? <Loading text="Building the map" /> : <Empty>Nothing to map yet.</Empty>}
        </Tile>
        <Tile title="Profile" className="lg:col-span-2">
          <Profile facts={dash.profile} running={running} openPanel={openPanel} />
        </Tile>
        <Tile title="Next step" className="lg:col-span-2">
          <NextStep ns={dash.next_step} past={past} onChanged={() => load(viewDate)} />
        </Tile>
        <Tile title="Lookup trail" className="md:col-span-2 lg:col-span-6">
          <Trail steps={dash.trail} running={running} openPanel={openPanel} />
        </Tile>
        <Tile title="Insurers" className="md:col-span-2 lg:col-span-4">
          <Insurers ins={dash.insurers} running={running} openPanel={openPanel} />
        </Tile>
        <Tile title="Gaps" className="lg:col-span-2">
          <Gaps d={dash} running={running} />
        </Tile>
        <Tile title="Diary" className="lg:col-span-6">
          <Diary entries={dash.diary} openPanel={openPanel} />
        </Tile>
      </div>

      <p className={`text-sm ${muted}`}>Every fact shows where it came from. Click any row to see its source.</p>
    </div>
  );
}

function RunBanner({ status }: { status: Dash["run"]["status"] }) {
  const text = status === "running" ? "Checking now. The lookup trail fills in as each step finishes."
    : status === "held" ? "This check is paused and waiting. Nothing more will be looked up until it resumes."
    : status === "stopped" ? "The last check stopped before it finished. What is shown may be incomplete." : "";
  if (!text) return null;
  return <p role="status" className={`rounded-lg border ${line} px-4 py-3 text-sm`}>{text}</p>;
}

function Profile({ facts, running, openPanel }: { facts: Fact[]; running: boolean; openPanel: (p: Panel) => void }) {
  if (!facts?.length) return running ? <Loading text="Reading your work record" /> : <Empty>No facts on record for this date.</Empty>;
  return (
    <ul className="divide-y divide-neutral-200 dark:divide-neutral-800">
      {facts.map((f) => (
        <li key={f.fact_id}>
          <button type="button" className="w-full py-2.5 text-left" onClick={() => openPanel(sourcePanel(nice(f.statement), f.source,
            f.cannot_verify ? <p><CannotVerify missing={f.missing} /></p> : undefined))}>
            <div className="flex items-start gap-3">
              <span className="min-w-0 flex-1 text-sm">{nice(f.statement)}</span>
              <LabelTag label={f.label} />
            </div>
            {(f.last_checked || f.cannot_verify) && (
              <div className={`mt-0.5 text-xs ${muted}`}>
                {f.cannot_verify ? <CannotVerify missing={f.missing} /> : `checked ${day(f.last_checked)}`}
              </div>
            )}
          </button>
        </li>
      ))}
    </ul>
  );
}

const modeText = (s: TrailStep) => s.mode === "live" ? "Live" : s.mode === "replay" ? `Replay${s.recorded_at ? `, recorded ${day(s.recorded_at)}` : ""}` : "No call";
const statusText: Record<TrailStep["status"], string> = { found: "Found", "searched, cannot verify": "Searched, cannot verify", skipped: "Skipped, not done", computed: "Worked out", running: "In progress" };

function Trail({ steps, running, openPanel }: { steps: TrailStep[]; running: boolean; openPanel: (p: Panel) => void }) {
  const [open, setOpen] = useState<string | null>(null);
  const have = steps || [];
  if (!have.length && !running) return <Empty>No lookups yet.</Empty>;
  const waiting = running ? STEP_ORDER.filter((s) => !have.some((h) => h.key === s.key)) : [];
  return (
    <ol className="grid items-start gap-2 sm:grid-cols-2 lg:grid-cols-5">
      {have.map((s, i) => {
        const skipped = s.status === "skipped";
        const isOpen = open === s.key;
        return (
          <li key={s.key} className={`rounded-lg border ${skipped ? "border-dashed border-neutral-300 dark:border-neutral-700" : line}`}>
            <button type="button" aria-expanded={isOpen} onClick={() => setOpen(isOpen ? null : s.key)} className="w-full p-3 text-left">
              <div className="flex items-baseline gap-2">
                <span className={`text-xs tabular-nums ${muted}`}>{i + 1}</span>
                <span className={`mr-auto text-sm font-medium ${skipped ? "text-neutral-400 line-through dark:text-neutral-500" : ""}`}>{s.title}</span>
                <span className={`text-xs ${s.status === "running" ? "text-blue-600 dark:text-blue-400" : skipped ? muted : ""}`}>{statusText[s.status] ?? s.status}</span>
              </div>
              <dl className={`mt-1.5 grid grid-cols-[auto_1fr] gap-x-3 gap-y-0.5 text-xs ${skipped ? "text-neutral-400 dark:text-neutral-500" : muted}`}>
                <dt>Searched</dt><dd className="min-w-0 break-words">{s.searched}</dd>
                <dt>Source</dt><dd className="min-w-0 break-words">{s.source}</dd>
                <dt>Records</dt><dd>{s.records ?? "Not counted"}</dd>
                <dt>Credits</dt><dd>{s.credits}</dd>
                <dt>Data</dt><dd>{modeText(s)}{s.reused ? " · reused" : ""}</dd>
              </dl>
              {s.note && <p className={`mt-1.5 text-xs ${muted}`}>{s.note}</p>}
            </button>
            {isOpen && (
              <div className={`border-t ${line} p-3`}>
                {s.pointers?.length ? (
                  <ul className="space-y-1">
                    {s.pointers.map((p, j) => (
                      <li key={j}><button type="button" className="w-full text-left text-xs underline-offset-2 hover:underline" onClick={() => openPanel(sourcePanel(`${s.title}: source`, p))}>
                        {p.record}{p.field_path ? ` · ${p.field_path}` : ""}{p.record_date ? ` · ${day(p.record_date)}` : ""}
                      </button></li>
                    ))}
                  </ul>
                ) : <Empty>No records for this step.</Empty>}
              </div>
            )}
          </li>
        );
      })}
      {waiting.map((s) => (
        <li key={s.key} className={`rounded-lg border border-dashed border-neutral-300 p-3 text-sm dark:border-neutral-700 ${muted}`}>
          {s.title} <span className="text-xs">· waiting</span>
        </li>
      ))}
    </ol>
  );
}

const val = (v: unknown) => (v == null ? "Not given" : typeof v === "object" ? JSON.stringify(v) : String(v));

function Insurers({ ins, running, openPanel }: { ins: Dash["insurers"]; running: boolean; openPanel: (p: Panel) => void }) {
  const items: Insurer[] = ins?.items || [];
  return (
    <div className="space-y-4">
      <p className="text-sm">{ins?.note || "These are company facts, not a measure of how well they pay claims."}</p>
      {!items.length ? (
        running ? <Loading text="Looking up insurers" /> : (
          <div className="text-sm">
            {ins?.missing ? <CannotVerify missing={ins.missing} /> : <Empty>{ins?.status ? `No insurers: ${ins.status}` : "No insurers yet."}</Empty>}
          </div>
        )
      ) : (
        <ul className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
          {items.map((it) => (
            <li key={it.company_id} className={`rounded-lg border ${line} p-4`}>
              <div className="mb-2 font-medium">{it.name}</div>
              {it.facts.length ? (
                <ul className="space-y-2">
                  {it.facts.map((f, i) => (
                    <li key={i}>
                      <button type="button" className="w-full text-left" onClick={() => openPanel(sourcePanel(`${it.name}: ${f.label}`, f.source))}>
                        <div className="text-sm"><span className={muted}>{f.label}: </span>{val(f.value)}</div>
                        <div className={`text-xs ${muted}`}>{f.source?.field_path || f.source?.record}{f.source?.record_date ? ` · ${day(f.source.record_date)}` : ""}</div>
                      </button>
                    </li>
                  ))}
                </ul>
              ) : <Empty>No company facts found.</Empty>}
              <div className={`mt-3 border-t ${line} pt-2`}>
                <div className={`text-xs ${muted}`}>From the regulator</div>
                {Array.isArray(it.claims) ? (
                  it.claims.length ? (
                    <>
                      {it.claims.map((c: any, i: number) => (
                        <button key={i} type="button" className="block w-full text-left text-sm" onClick={() => openPanel(sourcePanel(`${it.name}: ${c.label || "claims"}`, c.source))}>
                          <span className={muted}>{c.label ? `${c.label}: ` : ""}</span>{c.value}
                          <div className={`text-xs ${muted}`}>{c.source?.field_path}</div>
                        </button>
                      ))}
                      {(it.claims[0] as any)?.meaning && <p className={`mt-1 text-xs ${muted}`}>This is {(it.claims[0] as any).meaning}</p>}
                    </>
                  ) : <CannotVerify />
                ) : <CannotVerify missing={it.claims.missing} />}
                {(it as any).complaints?.cannot_verify && <div className="mt-2"><div className={`text-xs ${muted}`}>Complaints</div><CannotVerify missing={(it as any).complaints.missing} /></div>}
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

function Gaps({ d, running }: { d: Dash; running: boolean }) {
  return (
    <div className="space-y-4">
      {!d.gaps?.length ? (running ? <Loading text="Applying the rules" /> : <Empty>No rule found a gap for this date.</Empty>) : (
        <ul className="divide-y divide-neutral-200 dark:divide-neutral-800">
          {d.gaps.map((g) => (
            <li key={g.rule_id} className="py-2.5 text-sm">
              <span className="mr-2 font-mono text-xs">{g.rule_id}</span>{g.explanation}
              <div className={`mt-0.5 text-xs ${muted}`}>Facts used: {g.facts_used.length ? g.facts_used.join(", ") : "none"}</div>
            </li>
          ))}
        </ul>
      )}
      {d.questions?.length > 0 && (
        <div>
          <h3 className="mb-1 text-sm font-medium">We still need to ask</h3>
          <ul className="space-y-1 text-sm">{d.questions.map((q, i) => <li key={i}>{q.question} <span className={muted}>({q.why})</span></li>)}</ul>
        </div>
      )}
      {d.cannot_verify?.length > 0 && (
        <div>
          <h3 className="mb-1 text-sm font-medium">Cannot verify</h3>
          <ul className="space-y-1 text-sm">{d.cannot_verify.map((c, i) => <li key={i}>{c.statement}: <span className={muted}>missing {c.missing}</span></li>)}</ul>
        </div>
      )}
    </div>
  );
}

function Diary({ entries, openPanel }: { entries: DiaryEntry[]; openPanel: (p: Panel) => void }) {
  if (!entries?.length) return <Empty>No changes recorded yet. Each check that finds something new adds a line here.</Empty>;
  return (
    <ul className="divide-y divide-neutral-200 dark:divide-neutral-800">
      {entries.map((e, i) => (
        <li key={i}>
          <button type="button" className="w-full py-2.5 text-left" onClick={() => openPanel(sourcePanel(`${e.subject}: ${e.new}`, e.source))}>
            <div className="flex flex-wrap items-baseline gap-x-3 gap-y-1">
              <span className={`text-xs tabular-nums ${muted}`}>{day(e.date)}</span>
              <span className="text-sm font-medium">{e.subject}</span>
              <span className="ml-auto flex gap-1.5"><LabelTag label={e.label} />{e.gap_changed && <Tag>gap changed</Tag>}{e.next_step_changed && <Tag>next step changed</Tag>}</span>
            </div>
            <div className="mt-1 text-sm">{e.new}{e.previous != null && <span className={muted}> (was {e.previous})</span>}</div>
            <div className={`text-xs ${muted}`}>Why: {e.trigger}</div>
          </button>
        </li>
      ))}
    </ul>
  );
}

function Fields({ obj }: { obj: Record<string, any> }) {
  const rows = Object.entries(obj).filter(([k, v]) => v != null && typeof v !== "object" && !/(^|_)(key|run_id|id)$/.test(k));
  return (
    <dl className="grid grid-cols-[auto_1fr] gap-x-3 gap-y-1 text-sm">
      {rows.map(([k, v]) => (<Fragment key={k}><dt className={muted}>{k.replace(/_/g, " ")}</dt><dd className="min-w-0 break-words">{String(v)}</dd></Fragment>))}
    </dl>
  );
}

function NextStep({ ns, past, onChanged }: { ns: Dash["next_step"]; past: boolean; onChanged: () => void }) {
  const [action, setAction] = useState<any | null>(ns?.action ?? null);
  const [repick, setRepick] = useState(false);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");
  const [count, setCount] = useState<number | null>(null);
  useEffect(() => { if (ns?.action) setAction(ns.action); }, [ns?.action?.key, ns?.action?.status]); // eslint-disable-line react-hooks/exhaustive-deps

  const key: string | undefined = action?.key;
  useEffect(() => {
    if (!key) return;
    let stop = false;
    const tick = async () => {
      try {
        const sb = await api<any>("/api/sandbox");
        const list: any[] = Array.isArray(sb) ? sb : Array.isArray(sb?.receipts) ? sb.receipts : [];
        const r = list.find((x) => x.key === key);
        if (!stop) setCount(r ? Number(r.count) || 0 : 0);
      } catch { if (!stop) setCount(null); }
    };
    tick();
    const t = setInterval(tick, 1500);
    return () => { stop = true; clearInterval(t); };
  }, [key]);

  async function choose(company_id: number) {
    setBusy(true); setErr("");
    try { const r = await api<{ action: any }>("/api/choose", { company_id }); setAction(r.action); setRepick(false); onChanged(); }
    catch (e) { setErr(errText(e)); } finally { setBusy(false); }
  }
  async function approve() {
    setBusy(true); setErr("");
    try {
      await api("/api/approve", { key: action.key, approver: "person" });
      setAction({ ...action, status: action.status === "done" ? "done" : "approved", approved_by: "person" });
      await api("/api/act", { run_id: action.run_id });
      onChanged();
    } catch (e) { setErr(errText(e)); } finally { setBusy(false); }
  }

  const choices = ns?.choices || [];
  const approved = action && (action.approved_by || ["approved", "sending", "done"].includes(action.status));
  return (
    <div className="space-y-4">
      {(!action || repick) ? (
        choices.length ? (
          <div>
            <p className="mb-3 text-sm">Pick an insurer and the broker will prepare an application. Nothing is sent until you approve it.</p>
            <div className="flex flex-wrap gap-2" role="group" aria-label="Choose an insurer">
              {choices.map((c) => <Button key={c.company_id} disabled={busy || past} onClick={() => choose(c.company_id)}>{c.name}</Button>)}
            </div>
            {past && <p className={`mt-2 text-xs ${muted}`}>Go back to Today to choose.</p>}
            {repick && <Button kind="quiet" className="mt-2" onClick={() => setRepick(false)}>Cancel</Button>}
          </div>
        ) : <Empty>No next step yet. It appears once a gap and insurers are found.</Empty>
      ) : (
        <div className={`rounded-lg border ${line} p-4`}>
          <div className="font-medium">{action.summary || "Prepared application"}</div>
          <div className="mt-2"><Fields obj={{ status: action.status, can_be_undone: action.reversible == null ? undefined : action.reversible ? "Yes" : "No", cost: action.cost_note, approved_by: action.approved_by }} /></div>
          <div className="mt-4 flex flex-wrap items-center gap-3">
            <Button kind="primary" disabled={busy || !!approved || past} onClick={approve}>{approved ? "Approved" : busy ? "Approving…" : "Approve"}</Button>
            {!approved && choices.length > 1 && <Button kind="quiet" onClick={() => setRepick(true)}>Choose another insurer</Button>}
          </div>
          <p className="mt-3 text-sm" role="status">
            <span className={muted}>Sandbox receipt: </span>
            <span className="font-medium">{count == null ? "Sandbox not reachable" : count === 0 ? "Not sent yet" : count === 1 ? "Sent once" : `Sent ${count} times`}</span>
          </p>
        </div>
      )}
      {ns?.conversion && (
        <div className={`rounded-lg border ${line} p-4`}>
          <div className="mb-2 font-medium">{ns.conversion.summary || "Converting your work cover"}</div>
          {typeof ns.conversion === "object" ? <Fields obj={ns.conversion} /> : <p className="text-sm">{String(ns.conversion)}</p>}
        </div>
      )}
      <ErrorText>{err}</ErrorText>
    </div>
  );
}
