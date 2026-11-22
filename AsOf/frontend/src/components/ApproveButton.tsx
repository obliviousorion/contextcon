import React, { useState } from "react";
import { ShieldCheck, Clock, CheckCircle2 } from "lucide-react";

interface ApproveButtonProps {
  initialStatus?: "draft" | "approved" | "issued_sandbox";
  onApproved?: () => void;
}

type ApprovalState = "draft" | "held_for_approval" | "issued_sandbox";

export const ApproveButton: React.FC<ApproveButtonProps> = ({
  initialStatus = "draft",
  onApproved,
}) => {
  const [approvalState, setApprovalState] = useState<ApprovalState>(
    initialStatus === "issued_sandbox" ? "issued_sandbox" : "draft"
  );
  const [isDisabled, setIsDisabled] = useState<boolean>(initialStatus === "issued_sandbox");

  const handleApprove = () => {
    if (isDisabled) return;

    // Disables after one click
    setIsDisabled(true);
    // Transitions to "held for approval"
    setApprovalState("held_for_approval");

    // Transitions to "issued (sandbox)"
    setTimeout(() => {
      setApprovalState("issued_sandbox");
      if (onApproved) {
        onApproved();
      }
    }, 900);
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
        {approvalState === "held_for_approval" && "Processing approval..."}
        {approvalState === "issued_sandbox" && "Issued to sandbox"}
      </button>
    </div>
  );
};
