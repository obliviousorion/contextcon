import { useState, type FormEvent } from "react";
import { useFocusTrap } from "../lib/useFocusTrap";

interface Props {
  open: boolean;
  artifactId: string;
  pending: boolean;
  error: string | null;
  onSubmit: (token: string) => void;
  onClose: () => void;
}

/** Accessible modal asking a person for the approval token printed by the API server. */
export function TokenDialog({ open, artifactId, pending, error, onSubmit, onClose }: Props) {
  const [token, setToken] = useState("");
  const ref = useFocusTrap<HTMLFormElement>(open, () => !pending && onClose());
  if (!open) return null;

  const submit = (e: FormEvent) => {
    e.preventDefault();
    if (token.trim() && !pending) onSubmit(token);
  };

  return (
    <div className="fixed inset-0 z-modal flex items-center justify-center p-4">
      <div className="scrim absolute inset-0" aria-hidden="true" />
      <form
        ref={ref}
        onSubmit={submit}
        role="dialog"
        aria-modal="true"
        aria-labelledby="token-title"
        aria-describedby="token-desc"
        className="surface relative w-full max-w-md p-6"
      >
        <h2 id="token-title" className="text-xl">Held for approval</h2>
        <div id="token-desc" className="mt-2 space-y-2 text-ink">
          <p>
            <span className="font-mono text-sm">{artifactId}</span> has not been sent. Approving is a person's act:
            nothing that only calls the API can approve.
          </p>
          <p className="text-muted">
            Paste the approval token printed in the API server's terminal (the line starting
            “Approval token for this session”). Or approve from the CLI:{" "}
            <code className="font-mono text-meta text-ink">uv run python -m backend.cli approve {artifactId}</code>
          </p>
        </div>

        <label htmlFor="approval-token" className="label mt-4">Approval token</label>
        <input
          id="approval-token"
          data-autofocus
          className="input font-mono"
          autoComplete="off"
          spellCheck={false}
          value={token}
          onChange={(e) => setToken(e.target.value)}
          aria-invalid={error ? true : undefined}
          aria-describedby={error ? "token-error" : undefined}
        />
        {error && (
          <p id="token-error" role="alert" className="mt-2 text-sm text-danger">{error}</p>
        )}

        <div className="mt-5 flex flex-wrap justify-end gap-2">
          <button type="button" className="btn-secondary" onClick={onClose} disabled={pending}>
            Cancel, keep held
          </button>
          <button type="submit" className="btn-primary" disabled={pending || !token.trim()}>
            {pending ? "Approving…" : "Approve and issue"}
          </button>
        </div>
      </form>
    </div>
  );
}
