// Guided flow v2 (web/GUIDED_CONTRACT.md): Login -> Confirm card -> Two questions -> Dashboard.
import { useCallback, useEffect, useState } from "react";
import { api, errText, type Me, type Stage } from "./api";
import Login from "./Login";
import Confirm from "./Confirm";
import Questions from "./Questions";
import Dashboard from "./Dashboard";
import { Button, Confirm as ConfirmDialog, ErrorText, Loading, SidePanel, line, muted, type Panel } from "./ui";

type View = "boot" | "login" | Stage;
const FONT = 'system-ui, -apple-system, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif';

function useTheme() {
  const [dark, setDark] = useState(() => !!window.matchMedia?.("(prefers-color-scheme: dark)").matches);
  useEffect(() => {
    document.documentElement.classList.toggle("dark", dark);
    document.body.style.background = dark ? "#0a0a0a" : "#ffffff";
    document.body.style.color = dark ? "#fafafa" : "#0a0a0a";
  }, [dark]);
  return [dark, setDark] as const;
}

export default function Guided() {
  const [dark, setDark] = useTheme();
  const [view, setView] = useState<View>("boot");
  const [bootErr, setBootErr] = useState("");
  const [panel, setPanel] = useState<Panel>(null);
  const [refusal, setRefusal] = useState("");
  const [notice, setNotice] = useState<React.ReactNode>(null);
  const [askForget, setAskForget] = useState(false);
  const [err, setErr] = useState("");

  const boot = useCallback(() => {
    setBootErr("");
    api<Me>("/api/me")
      .then((m) => setView(m.logged_in && m.stage ? m.stage : "login"))
      .catch((e) => setBootErr(errText(e)));
  }, []);
  useEffect(boot, [boot]);

  const closePanel = useCallback(() => setPanel(null), []);
  const toLogin = useCallback(() => { setPanel(null); setView("login"); }, []);
  const loggedIn = view !== "boot" && view !== "login";

  async function logout() {
    try { await api("/api/logout", {}); } catch { /* leave anyway */ }
    setNotice(null); toLogin();
  }
  async function forget() {
    setAskForget(false); setErr("");
    try {
      const r = await api<{ deleted: Record<string, number>; note?: string }>("/api/forget", {});
      const rows = Object.entries(r.deleted || {});
      setNotice(
        <div>
          <p className="font-medium">Your data was deleted.</p>
          {rows.length > 0 && (
            <ul className={`mt-2 grid grid-cols-[1fr_auto] gap-x-6 gap-y-0.5 ${muted}`}>
              {rows.map(([t, n]) => <li key={t} className="contents"><span>{t.replace(/_/g, " ")}</span><span className="tabular-nums">{n} rows</span></li>)}
            </ul>
          )}
          {r.note && <p className={`mt-2 ${muted}`}>{r.note}</p>}
        </div>,
      );
      toLogin();
    } catch (e) { setErr(errText(e)); }
  }

  return (
    <div className="gd min-h-screen bg-white text-neutral-900 dark:bg-[#0a0a0a] dark:text-neutral-100" style={{ fontFamily: FONT }}>
      <style>{`.gd :focus-visible{outline:2px solid #2563eb;outline-offset:2px;border-radius:8px}.dark .gd :focus-visible{outline-color:#60a5fa}.gd-graph .grid>div{min-width:0}.gd-graph canvas{display:block}`}</style>
      <header className={`border-b ${line}`}>
        <div className="mx-auto flex max-w-[1440px] flex-wrap items-center gap-x-4 gap-y-2 px-4 py-4 sm:px-8">
          <div className="mr-auto">
            <div className="text-base font-semibold">Benefits Desk</div>
            <div className={`text-xs ${muted}`}>For a licensed broker. Nothing is bought or sent without your approval.</div>
          </div>
          <nav className="flex flex-wrap items-center gap-2" aria-label="Page">
            <Button kind="quiet" onClick={() => setDark(!dark)} aria-label={`Switch to ${dark ? "light" : "dark"} theme`}>{dark ? "Light" : "Dark"}</Button>
            <a href="/console" className="px-2 text-sm text-neutral-600 underline-offset-4 hover:underline dark:text-neutral-300">Console</a>
            {loggedIn && <Button onClick={logout}>Log out</Button>}
            {loggedIn && <Button onClick={() => setAskForget(true)}>Forget me</Button>}
          </nav>
        </div>
      </header>

      <main className="mx-auto max-w-[1440px] px-4 sm:px-8">
        {err && <div className="pt-4"><ErrorText>{err}</ErrorText></div>}
        {view === "boot" && (
          <div className="py-10">{bootErr ? <div className="space-y-3"><ErrorText>{bootErr}</ErrorText><Button onClick={boot}>Try again</Button></div> : <Loading />}</div>
        )}
        {view === "login" && <Login notice={notice} onIn={(s) => { setNotice(null); setView(s); }} />}
        {view === "confirm" && (
          <Confirm openPanel={setPanel} onDone={(s, m) => { if (m) setRefusal(m); setView(s); }} />
        )}
        {view === "questions" && <Questions onDone={() => setView("dashboard")} />}
        {view === "dashboard" && <Dashboard dark={dark} openPanel={setPanel} onLoggedOut={toLogin} />}
        {view === "refused" && (
          <div className="mx-auto max-w-md py-10">
            <h1 className="text-2xl font-semibold">We stopped here</h1>
            <p className="mt-3 text-sm">{refusal || "This profile cannot be used in this demo. Nothing more will be looked up."}</p>
            <div className={`mt-6 border-t ${line} pt-6`}><Button onClick={logout}>Back to sign in</Button></div>
          </div>
        )}
      </main>

      <SidePanel panel={panel} onClose={closePanel} />
      {askForget && (
        <ConfirmDialog text="Delete everything we stored about you? This cannot be undone." yes="Forget me"
          onYes={forget} onNo={() => setAskForget(false)} />
      )}
    </div>
  );
}
