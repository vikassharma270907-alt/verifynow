import { useState } from "react";
import type { ClaimVerification } from "../hooks/useVerification";
import EvidenceChain from "./EvidenceChain";

interface Props { verification: ClaimVerification }

const cfg: Record<string, { icon: string; bg: string; border: string; badge: string; badgeBg: string }> = {
  verified:     { icon: "✓", bg: "var(--verified-soft)",     border: "#D1FAE5", badge: "var(--verified)",     badgeBg: "#D1FAE5" },
  unverifiable: { icon: "?", bg: "var(--unverifiable-soft)",  border: "#FEF3C7", badge: "var(--unverifiable)",  badgeBg: "#FEF3C7" },
  contradicted: { icon: "✕", bg: "var(--contradicted-soft)",  border: "#FECACA", badge: "var(--contradicted)",  badgeBg: "#FECACA" },
  pending:      { icon: "…", bg: "var(--surface)",           border: "var(--border)", badge: "var(--text-tertiary)", badgeBg: "#F3F4F6" },
};

export default function ClaimCard({ verification }: Props) {
  const [open, setOpen] = useState(false);
  const { claim, evidence, verdict } = verification;
  const c = cfg[verdict] ?? cfg.pending;

  return (
    <div className="rounded-lg border transition-colors" style={{ background: c.bg, borderColor: c.border }}>
      <button onClick={() => setOpen(!open)} className="w-full text-left px-4 py-3 flex items-start gap-3" aria-expanded={open}>
        <span className="mt-px w-5 h-5 rounded flex items-center justify-center text-[11px] font-bold shrink-0"
          style={{ background: c.badgeBg, color: c.badge }}>{c.icon}</span>
        <div className="flex-1 min-w-0">
          <p className="text-[14px] font-medium leading-snug" style={{ color: "var(--text-primary)" }}>{claim.text}</p>
          <div className="flex flex-wrap gap-1.5 mt-1.5">
            <Tag>{claim.category}</Tag><Tag>{claim.source_location}</Tag><Tag>{(claim.confidence * 100).toFixed(0)}%</Tag>
          </div>
          {claim.verification_reason && (
            <p className="text-xs mt-1.5" style={{ color: "var(--text-secondary)", lineHeight: 1.5 }}>{claim.verification_reason}</p>
          )}
        </div>
        <span className="shrink-0 text-xs flex items-center gap-0.5 mt-0.5" style={{ color: "var(--text-tertiary)" }}>
          {evidence.length}
          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"
            style={{ transform: open ? "rotate(180deg)" : "rotate(0)", transition: "transform 0.15s" }}>
            <polyline points="6 9 12 15 18 9" />
          </svg>
        </span>
      </button>
      {open && evidence.length > 0 && (
        <div className="px-3 sm:px-4 pb-3 sm:pb-4 ml-0 sm:ml-8">
          <div className="border-t pt-3" style={{ borderColor: c.border }}><EvidenceChain evidence={evidence} /></div>
        </div>
      )}
    </div>
  );
}

function Tag({ children }: { children: React.ReactNode }) {
  return (
    <span className="text-[10px] font-medium px-1.5 py-0.5 rounded"
      style={{ background: "rgba(255,255,255,0.7)", color: "var(--text-secondary)", border: "1px solid var(--border)" }}>
      {children}
    </span>
  );
}
