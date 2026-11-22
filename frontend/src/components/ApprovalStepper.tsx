import type { ApprovalRecord } from "../types";
import { fmtDateTime } from "../lib/format";
import { useIssueFlow, type Phase } from "../lib/useIssueFlow";
import { TokenDialog } from "./TokenDialog";

interface Props {
  id: string;
  status?: string;
  approval?: ApprovalRecord | null;
  /** What is being sent, for the button label ("case file", "audit report", ...). */
  noun: string;
  /** Runs before the first issue call (e.g. store an evidence request so it has an id). */
  prepare?: () => Promise<void>;
  onPhase?: (p: Phase) => void;
  compact?: boolean;
}

const ORDER: Phase[] = ["draft", "held", "approved", "issued"];

export function ApprovalStepper({ id, status, approval, noun, prepare, onPhase, compact = false }: Props) {
  const flow = useIssueFlow(id, status, approval, onPhase);
  const at = ORDER.indexOf(flow.phase);
  const rec = flow.approval;

  const steps: { key: Phase; title: string; detail?: string }[] = [
    { key: "draft", title: "Draft" },
    { key: "held", title: "Held for approval" },
    {
      key: "approved",
      title: "Approved",
      detail: rec ? `by ${rec.by}, ${fmtDateTime(rec.at)}` : at >= 2 ? "by a person" : undefined,
    },
    { key: "issued", title: "Issued (sandbox)" },
  ];

  const onIssue = async () => {
    if (flow.pending) return;
    if (prepare) {
      try {
        await prepare();
      } catch {
        // prepare reports its own error; issuing would only fail with "create it first".
        return;
      }
    }
    await flow.issue();
  };

  return (
    <section aria-label={`Approval for ${noun}`} className={compact ? "" : "surface p-5"}>
      {!compact && <h2 className="text-lg">Approval</h2>}
      <ol className="mt-3 grid gap-2 sm:grid-cols-4">
        {steps.map((s, i) => {
          const done = i < at || (i === at && flow.phase === "issued");
          const current = i === at && flow.phase !== "issued";
          return (
            <li
              key={s.key}
              aria-current={current ? "step" : undefined}
              className={`border-t-2 pt-2 transition-colors duration-200 ${done ? "border-ok" : current ? "border-accent" : "border-line"}`}
            >
              <span className={`text-meta font-mono ${done ? "text-ok" : current ? "text-accent" : "text-muted"}`}>
                {i + 1} · {done ? "done" : current ? "now" : "next"}
              </span>
              <p className={`text-sm font-medium ${i <= at ? "text-ink" : "text-muted"}`}>{s.title}</p>
              {s.detail && <p className="text-meta text-muted">{s.detail}</p>}
            </li>
          );
        })}
      </ol>

      <div className="mt-4 flex flex-wrap items-center gap-3" aria-live="polite">
        {flow.phase === "issued" ? (
          <p className="text-ok">
            <span className="font-semibold">Sent exactly once</span> to the sandbox
            {flow.sentKey && <span className="font-mono text-meta text-muted"> · key {flow.sentKey.slice(0, 16)}</span>}
            .
          </p>
        ) : (
          <>
            <button type="button" className="btn-primary" onClick={onIssue} disabled={flow.pending}>
              {flow.pending ? "Working…" : flow.phase === "held" ? `Approve and issue ${noun}` : `Issue ${noun}`}
            </button>
            <span className="text-meta text-muted">
              Nothing leaves without a person's approval. Sends go only to the sandbox.
            </span>
          </>
        )}
      </div>
      {flow.error && (
        <p role="alert" className="mt-2 text-sm text-danger">
          <span className="font-medium">Not sent: </span>{flow.error}
        </p>
      )}

      <TokenDialog
        open={flow.tokenOpen}
        artifactId={id}
        pending={flow.pending}
        error={flow.tokenError}
        onSubmit={(t) => void flow.approveWith(t)}
        onClose={flow.closeToken}
      />
    </section>
  );
}
