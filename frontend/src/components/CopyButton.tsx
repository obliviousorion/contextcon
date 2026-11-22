import { useState } from "react";

export function CopyButton({ text, label = "Copy" }: { text: string; label?: string }) {
  const [done, setDone] = useState<"idle" | "copied" | "failed">("idle");

  const copy = async () => {
    try {
      await navigator.clipboard.writeText(text);
      setDone("copied");
    } catch {
      setDone("failed");
    }
    window.setTimeout(() => setDone("idle"), 1600);
  };

  return (
    <button type="button" onClick={copy} className="btn-secondary shrink-0 px-2 py-0.5 text-meta" aria-label={label}>
      <span aria-live="polite">{done === "copied" ? "Copied" : done === "failed" ? "Copy failed" : "Copy"}</span>
    </button>
  );
}
