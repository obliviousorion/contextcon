import { useHealth } from "../lib/health";
import { CopyButton } from "./CopyButton";

const START = "uv run python -m backend.http_api";

export function BackendDown() {
  const { state, recheck } = useHealth();
  return (
    <section role="alert" className="surface mx-auto max-w-file p-6" aria-labelledby="down-head">
      <h1 id="down-head" className="text-2xl">Backend not running</h1>
      <p className="mt-2 text-ink">
        The UI could not reach the AsOf API at <span className="font-mono text-sm">/api/health</span>. Start it from
        the repo root in another terminal (replay mode, 0 credits):
      </p>
      <div className="mt-3 flex items-center gap-2 rounded border border-line bg-sunken px-3 py-2">
        <code className="min-w-0 flex-1 break-all font-mono text-sm">{START}</code>
        <CopyButton text={START} label="Copy start command" />
      </div>
      <p className="mt-3 text-muted">
        It binds 127.0.0.1:8787 and prints an approval token you will need to approve anything.
      </p>
      {state.status === "down" && (
        <p className="mt-2 text-meta text-muted">Last error: <span className="font-mono">{state.error}</span></p>
      )}
      <button type="button" className="btn-primary mt-4" onClick={recheck}>Check again</button>
    </section>
  );
}
