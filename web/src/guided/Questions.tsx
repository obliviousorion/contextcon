import { useState } from "react";
import { api, errText } from "./api";
import { Button, ErrorText, muted } from "./ui";

type Q = { key: "dependants" | "insurance_now"; ask: string; help: string; choices: [string, string][]; alone: string[] };
const QS: Q[] = [
  { key: "dependants", ask: "Who depends on you?", help: "Anyone who would struggle for money if you could not earn. Pick all that apply.",
    choices: [["just_me", "Just me"], ["partner", "Partner"], ["children", "Children"], ["parents", "Parents"], ["not_sure", "Not sure"]],
    alone: ["just_me", "not_sure"] },
  { key: "insurance_now", ask: "Do you have any insurance now?", help: "Any kind counts: health, life or accident. Pick all that apply.",
    choices: [["from_work", "Yes, from work"], ["bought_myself", "Yes, I bought it myself"], ["none", "No"], ["not_sure", "Not sure"]],
    alone: ["none", "not_sure"] },
];

export default function Questions({ onDone }: { onDone: (runId: string) => void }) {
  const [i, setI] = useState(0);
  const [picked, setPicked] = useState<Record<string, string[]>>({ dependants: [], insurance_now: [] });
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");
  const q = QS[i];
  const cur = picked[q.key];

  function toggle(v: string) {
    let next: string[];
    if (cur.includes(v)) next = cur.filter((x) => x !== v);
    else if (q.alone.includes(v)) next = [v];                       // "Just me", "No", "Not sure" stand alone
    else next = [...cur.filter((x) => !q.alone.includes(x)), v];
    setPicked({ ...picked, [q.key]: next });
  }

  async function next() {
    if (i < QS.length - 1) { setI(i + 1); return; }
    setBusy(true); setErr("");
    try {
      const r = await api<{ run_id: string }>("/api/answers", { dependants: picked.dependants, insurance_now: picked.insurance_now });
      onDone(r.run_id);
    } catch (e) { setErr(errText(e)); setBusy(false); }
  }

  return (
    <div className="mx-auto max-w-xl py-10">
      <p className={`text-sm ${muted}`}>Question {i + 1} of {QS.length}</p>
      <h1 id="q" className="mt-2 text-2xl font-semibold">{q.ask}</h1>
      <p className={`mt-2 text-sm ${muted}`}>{q.help}</p>
      <div role="group" aria-labelledby="q" className="mt-8 flex flex-col gap-2">
        {q.choices.map(([v, label]) => (
          <Button key={v} pressed={cur.includes(v)} onClick={() => toggle(v)} className="justify-start py-3 text-left text-base">{label}</Button>
        ))}
      </div>
      <div className="mt-8 space-y-3">
        <ErrorText>{err}</ErrorText>
        <div className="flex items-center gap-3">
          {i > 0 && <Button onClick={() => setI(i - 1)} disabled={busy}>Back</Button>}
          <Button kind="primary" disabled={!cur.length || busy} onClick={next}>{busy ? "Starting…" : "Continue"}</Button>
        </div>
      </div>
    </div>
  );
}
