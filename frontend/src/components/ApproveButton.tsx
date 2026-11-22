import React, { useState } from "react";
import { ShieldCheck, Clock, CheckCircle2 } from "lucide-react";

interface ApproveButtonProps {
  initialStatus?: "draft" | "approved" | "issued_sandbox";
  onApproved?: () => void;
  caseId?: string;
}

const API_BASE_URL = import.meta.env.VITE_API_URL as string | undefined;

async function post(path: string, body: unknown, token?: string) {
  const headers: Record<string, string> = { "content-type": "application/json" };
  if (token) headers["x-asof-approval-token"] = token;
  const res = await fetch(`${API_BASE_URL}${path}`, { method: "POST", headers, body: JSON.stringify(body) });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.error || res.statusText);
  return data;
}

type ApprovalState = "draft" | "held_for_approval" | "issued_sandbox";

export const ApproveButton: React.FC<ApproveButtonProps> = ({
  initialStatus = "draft",
  onApproved,
  caseId,
}) => {
  const [approvalState, setApprovalState] = useState<ApprovalState>(
    initialStatus === "issued_sandbox" ? "issued_sandbox" : "draft"
  );
  const [isDisabled, setIsDisabled] = useState<boolean>(initialStatus === "issued_sandbox");

  const [error, setError] = useState<string | null>(null);

  const handleApprove = async () => {
    if (isDisabled) return;
    setIsDisabled(true);
    setError(null);
    setApprovalState("held_for_approval");

    if (!API_BASE_URL || !caseId) {
      // Fixture mode: no backend, so this only shows the state change.
      setTimeout(() => {
        setApprovalState("issued_sandbox");
        onApproved?.();
      }, 900);
      return;
    }

    try {
      // 1. Ask to issue: the backend holds it until a person approves.
      const first = await post("/api/issue", { id: caseId });
      if (first.status !== "done") {
        // 2. A person approves with the token printed in the API server's terminal.
        const token = window.prompt(
          `Held for approval: ${caseId}\nPaste the approval token from the AsOf API server's terminal to approve and issue.`
        );
        if (!token) {
          setApprovalState("held_for_approval");
          setError("Held for approval: nothing was sent.");
          setIsDisabled(false);
          return;
        }
        await post("/api/approve", { id: caseId }, token);
        // 3. Issue again: now it is sent exactly once to the sandbox.
        const sent = await post("/api/issue", { id: caseId });
        if (sent.status !== "done") throw new Error(`issue returned ${sent.status}`);
      }
      setApprovalState("issued_sandbox");
      onApproved?.();
    } catch (e) {
      setApprovalState("held_for_approval");
      setError((e as Error).message);
      setIsDisabled(false);
    }
  };

  return (
    <div className="flex items-center gap-3">
      {/* State Chip */}
      {approvalState === "draft" && (
        <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-medium bg-slate-800 text-slate-300 border border-slate-700">
          <span className="w-1.5 h-1.5 rounded-full bg-slate-400"></span>
          draft
        </span>
      )}

      {approvalState === "held_for_approval" && (
        <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-medium bg-amber-950/70 text-amber-300 border border-amber-800/80 animate-pulse">
          <Clock className="w-3.5 h-3.5 text-amber-400" />
          held for approval
        </span>
      )}

      {approvalState === "issued_sandbox" && (
        <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-medium bg-emerald-950/80 text-emerald-300 border border-emerald-700/80">
          <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
          issued (sandbox)
        </span>
      )}

      {/* Button */}
      <button
        onClick={handleApprove}
        disabled={isDisabled}
        className={`inline-flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-semibold transition-all duration-200 shadow-sm ${
          isDisabled
            ? "bg-slate-800/80 text-slate-500 cursor-not-allowed border border-slate-700/50"
            : "bg-emerald-600 hover:bg-emerald-500 text-white shadow-emerald-950/50 hover:shadow-md cursor-pointer active:scale-95"
        }`}
      >
        <ShieldCheck className="w-4 h-4" />
        {approvalState === "draft" && "Approve & issue"}
        {approvalState === "held_for_approval" && (error ? "Approve & issue" : "Waiting for approval...")}
        {approvalState === "issued_sandbox" && "Issued to sandbox"}
      </button>
      {error && <span className="text-xs text-rose-300 max-w-xs">{error}</span>}
    </div>
  );
};
