import { useCallback, useRef, useState } from "react";
import type { ApprovalRecord } from "../types";
import { ApiError, api, errorMessage } from "./api";

export type Phase = "draft" | "held" | "approved" | "issued";

export interface IssueFlow {
  phase: Phase;
  pending: boolean;
  error: string | null;
  approval: ApprovalRecord | null;
  sentKey: string | null;
  tokenOpen: boolean;
  tokenError: string | null;
  /** Ask to issue. Held items open the token dialog; nothing is sent without approval. */
  issue: () => Promise<void>;
  /** A person pastes the token: approve, then issue (sent exactly once). */
  approveWith: (token: string) => Promise<void>;
  closeToken: () => void;
}

function initialPhase(status: string | undefined): Phase {
  if (status === "issued_sandbox" || status === "sent_sandbox") return "issued";
  if (status === "approved") return "approved";
  return "draft";
}

/**
 * The approval flow every outgoing artifact shares: issue -> held -> approve (token) -> issue.
 * A ref guards against double clicks, on top of the disabled buttons.
 */
export function useIssueFlow(id: string | null, status?: string, approval?: ApprovalRecord | null,
  onChange?: (phase: Phase) => void): IssueFlow {
  const [phase, setPhaseState] = useState<Phase>(initialPhase(status));
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [rec, setRec] = useState<ApprovalRecord | null>(approval ?? null);
  const [sentKey, setSentKey] = useState<string | null>(null);
  const [tokenOpen, setTokenOpen] = useState(false);
  const [tokenError, setTokenError] = useState<string | null>(null);
  const busy = useRef(false);

  const setPhase = useCallback((p: Phase) => {
    setPhaseState(p);
    onChange?.(p);
  }, [onChange]);

  const doIssue = useCallback(async (): Promise<"sent" | "held"> => {
    if (!id) throw new Error("nothing to issue");
    const r = await api.issue(id);
    if (r.status === "done" || r.status === "created") {
      setSentKey(r.key ?? r.watch_id ?? null);
      setPhase("issued");
      return "sent";
    }
    if (r.status === "held_for_approval") return "held";
    throw new Error(`issue returned ${r.status}${r.note ? `: ${r.note}` : ""}`);
  }, [id, setPhase]);

  const issue = useCallback(async () => {
    if (busy.current || !id) return;
    busy.current = true;
    setPending(true);
    setError(null);
    try {
      const out = await doIssue();
      if (out === "held") {
        setPhase("held");
        setTokenError(null);
        setTokenOpen(true);
      }
    } catch (e) {
      setError(errorMessage(e));
    } finally {
      busy.current = false;
      setPending(false);
    }
  }, [id, doIssue, setPhase]);

  const approveWith = useCallback(async (token: string) => {
    if (busy.current || !id) return;
    busy.current = true;
    setPending(true);
    setTokenError(null);
    try {
      try {
        const a = await api.approve(id, token.trim());
        if (a.status !== "approved") throw new Error(a.note ?? `approve returned ${a.status}`);
        setRec(a.approved_by && a.approved_at ? { by: a.approved_by, at: a.approved_at } : null);
        setPhase("approved");
      } catch (e) {
        // 409: already approved elsewhere (e.g. the CLI). Issuing is still safe: it sends only if approved.
        if (!(e instanceof ApiError && e.status === 409)) throw e;
        const out = await doIssue();
        if (out === "held") throw e;
        setTokenOpen(false);
        return;
      }
      const out = await doIssue();
      if (out === "held") throw new Error("approved, but issue is still held; try Issue again");
      setTokenOpen(false);
    } catch (e) {
      setTokenError(errorMessage(e));
    } finally {
      busy.current = false;
      setPending(false);
    }
  }, [id, doIssue, setPhase]);

  const closeToken = useCallback(() => setTokenOpen(false), []);

  return { phase, pending, error, approval: rec, sentKey, tokenOpen, tokenError, issue, approveWith, closeToken };
}
