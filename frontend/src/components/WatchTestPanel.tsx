import { useRef, useState } from "react";
import { Link } from "react-router-dom";
import { api, errorMessage } from "../lib/api";
import { fmtCredits, fmtInr } from "../lib/format";
import { useHealth } from "../lib/health";
import type { WatchTestResponse } from "../types";
import { LineRow } from "./LineRow";


/** Fires the free /test alert and shows which stored lines it marked STALE. */
export function WatchTestPanel({ id }: { id: string }) {
  const { state } = useHealth();
  const ALERT_CREDITS = state.status === "up" ? state.health.watch_alert_credits : 5;
  const INR_PER_CREDIT = state.status === "up" ? state.health.inr_per_credit : 0;
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [res, setRes] = useState<WatchTestResponse | null>(null);
  const busy = useRef(false);

  const fire = async () => {
    if (busy.current) return;
    busy.current = true;
    setPending(true);
    setError(null);
    try {
      setRes(await api.watchTest(id));
    } catch (e) {
      setError(errorMessage(e));
    } finally {
      busy.current = false;
      setPending(false);
    }
  };

  return (
    <section className="surface" aria-labelledby="test-head">
      <div className="border-b border-line p-5">
        <h2 id="test-head" className="text-lg">Test alert</h2>
        <p className="mt-1 text-ink">
          The test alert is free. A real alert costs {fmtCredits(ALERT_CREDITS)} {INR_PER_CREDIT ? <> (about {fmtInr(ALERT_CREDITS * INR_PER_CREDIT)})</> : null},
          capped per company per month.
        </p>
        <button type="button" className="btn-primary mt-3" onClick={fire} disabled={pending}>
          {pending ? "Firing…" : "Fire test alert (free)"}
        </button>
        {error && <p role="alert" className="mt-2 text-sm text-danger">{error}</p>}
      </div>

      {res && (
        <div aria-live="polite">
          <div className="p-5">
            {res.status === "alert" ? (
              <>
                <p className="font-semibold">
                  Alert recorded for signal date <span className="font-mono">{res.snapshot.signal_date}</span>.
                </p>
                {res.stale_line_ids.length === 0 ? (
                  <p className="mt-1 text-muted">No stored case file has this line, so nothing was marked STALE.</p>
                ) : (
                  <ul className="mt-2 space-y-1">
                    {res.stale_line_ids.map((sid) => {
                      const [cf, field] = sid.split("#");
                      return (
                        <li key={sid} className="flex flex-wrap items-center gap-2">
                          <span className="chip bg-stale-tint text-stale">Stale</span>
                          <span className="font-mono text-sm">{sid}</span>
                          <Link to={`/files/${cf}`} className="btn-link text-sm">Open {cf} ({field})</Link>
                        </li>
                      );
                    })}
                  </ul>
                )}
              </>
            ) : (
              <p className="text-ink">
                <span className="font-semibold">No new alert: </span>{res.reason}. Nothing changed.
              </p>
            )}
          </div>
          <ol aria-label="Current line" className="border-t border-line">
            <LineRow line={res.current_line} evidence={{}} onOpenEvidence={() => undefined} />
          </ol>
        </div>
      )}
    </section>
  );
}
