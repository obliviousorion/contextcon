import { useCallback, useEffect, useState } from "react";
import { errorMessage } from "./api";

export type AsyncState<T> =
  | { status: "loading"; data: null; error: null }
  | { status: "error"; data: null; error: string }
  | { status: "success"; data: T; error: null };

/**
 * Runs `fn` whenever `deps` change; aborts the previous request. `retry` re-runs it.
 * `fn` gets an AbortSignal so stale responses never overwrite newer ones.
 */
export function useAsync<T>(fn: (signal: AbortSignal) => Promise<T>, deps: unknown[]) {
  const [state, setState] = useState<AsyncState<T>>({ status: "loading", data: null, error: null });
  const [nonce, setNonce] = useState(0);

  useEffect(() => {
    const ctrl = new AbortController();
    setState({ status: "loading", data: null, error: null });
    fn(ctrl.signal)
      .then((data) => {
        if (!ctrl.signal.aborted) setState({ status: "success", data, error: null });
      })
      .catch((e: unknown) => {
        if (!ctrl.signal.aborted) setState({ status: "error", data: null, error: errorMessage(e) });
      });
    return () => ctrl.abort();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [...deps, nonce]);

  const retry = useCallback(() => setNonce((n) => n + 1), []);
  /** Replace the data in place (e.g. after an approval changes a file's status). */
  const setData = useCallback((data: T) => setState({ status: "success", data, error: null }), []);
  return { ...state, retry, setData };
}
