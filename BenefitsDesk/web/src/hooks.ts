import { useCallback, useEffect, useRef, useState } from "react";

export function useAsync<T>(fn: () => Promise<T>, deps: unknown[], opts?: { enabled?: boolean }) {
  const enabled = opts?.enabled ?? true;
  const [data, setData] = useState<T | undefined>(undefined);
  const [error, setError] = useState<unknown>(undefined);
  const [loading, setLoading] = useState<boolean>(enabled);
  const seq = useRef(0);
  const fnRef = useRef(fn);
  fnRef.current = fn;

  const reload = useCallback(async (quiet = false) => {
    const my = ++seq.current;
    if (!quiet) setLoading(true);
    try {
      const d = await fnRef.current();
      if (my === seq.current) {
        setData(d);
        setError(undefined);
      }
    } catch (e) {
      if (my === seq.current) setError(e);
    } finally {
      if (my === seq.current) setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (!enabled) {
      setLoading(false);
      return;
    }
    setData(undefined);
    reload();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [...deps, enabled]);

  return { data, error, loading, reload, setData };
}

export function useInterval(cb: () => void, ms: number | null) {
  const ref = useRef(cb);
  ref.current = cb;
  useEffect(() => {
    if (ms === null) return;
    const id = window.setInterval(() => ref.current(), ms);
    return () => window.clearInterval(id);
  }, [ms]);
}
