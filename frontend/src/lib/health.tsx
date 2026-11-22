import { createContext, useCallback, useContext, useEffect, useState, type ReactNode } from "react";
import type { Health } from "../types";
import { api, errorMessage } from "./api";

type HealthState =
  | { status: "checking"; health: null; error: null }
  | { status: "down"; health: null; error: string }
  | { status: "up"; health: Health; error: null };

interface HealthCtx {
  state: HealthState;
  recheck: () => void;
  /** Today's date per the server (ASOF_TODAY), falling back to the browser's date. */
  today: string;
}

const Ctx = createContext<HealthCtx | null>(null);

function browserToday(): string {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
}

export function HealthProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState<HealthState>({ status: "checking", health: null, error: null });
  const [nonce, setNonce] = useState(0);

  useEffect(() => {
    const ctrl = new AbortController();
    setState({ status: "checking", health: null, error: null });
    api.health(ctrl.signal)
      .then((h) => setState({ status: "up", health: h, error: null }))
      .catch((e: unknown) => {
        if (!ctrl.signal.aborted) setState({ status: "down", health: null, error: errorMessage(e) });
      });
    return () => ctrl.abort();
  }, [nonce]);

  const recheck = useCallback(() => setNonce((n) => n + 1), []);
  const today = state.status === "up" ? state.health.today : browserToday();
  return <Ctx.Provider value={{ state, recheck, today }}>{children}</Ctx.Provider>;
}

export function useHealth(): HealthCtx {
  const v = useContext(Ctx);
  if (!v) throw new Error("useHealth must be used inside HealthProvider");
  return v;
}
