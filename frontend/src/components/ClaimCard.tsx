import { useState } from "react";
import type { ClaimVerification } from "../hooks/useVerification";
import EvidenceChain from "./EvidenceChain";

interface Props {
  verification: ClaimVerification;
}

const verdictConfig: Record<string, {
  icon: string; bg: string; border: string; badge: string; badgeText: string;
}> = {
  verified:     { icon: "✓", bg: "bg-emerald-50/60",  border: "border-emerald-200/60", badge: "bg-emerald-100", badgeText: "text-emerald-700" },
  unverifiable: { icon: "?", bg: "bg-amber-50/60",    border: "border-amber-200/60",   badge: "bg-amber-100",   badgeText: "text-amber-700" },
  contradicted: { icon: "✗", bg: "bg-red-50/60",      border: "border-red-200/60",     badge: "bg-red-100",     badgeText: "text-red-700" },
  pending:      { icon: "…", bg: "bg-slate-50/60",    border: "border-slate-200/60",   badge: "bg-slate-100",   badgeText: "text-slate-600" },
  rejected:     { icon: "⊘", bg: "bg-red-50/60",      border: "border-red-300/60",     badge: "bg-red-100",     badgeText: "text-red-700" },
};

export default function ClaimCard({ verification }: Props) {
  const [expanded, setExpanded] = useState(false);
  const { claim, evidence, verdict } = verification;
  const config = verdictConfig[verdict] ?? verdictConfig.pending;

  return (
    <div className={`rounded-xl border ${config.border} ${config.bg} transition-all duration-200`}>
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full text-left px-4 py-3.5 flex items-start gap-3"
        aria-expanded={expanded}
      >
        {/* Status icon */}
        <span className={`mt-0.5 w-6 h-6 rounded-md flex items-center justify-center text-xs font-bold shrink-0 ${config.badge} ${config.badgeText}`}>
          {config.icon}
        </span>

        {/* Claim content */}
        <div className="flex-1 min-w-0">
          <p className="text-sm font-medium text-slate-800 leading-snug">{claim.text}</p>

          {/* Tags */}
          <div className="flex flex-wrap items-center gap-1.5 mt-2">
            <Tag>{claim.category}</Tag>
            <Tag>{claim.source_location}</Tag>
            <Tag>
              {(claim.confidence * 100).toFixed(0)}% conf.
            </Tag>
          </div>

          {/* Reason */}
          {claim.verification_reason && (
            <p className="text-xs text-slate-500 mt-1.5 leading-relaxed">
              {claim.verification_reason}
            </p>
          )}
        </div>

        {/* Expand toggle */}
        <div className="shrink-0 flex items-center gap-1 text-xs text-slate-400 mt-1">
          <span>{evidence.length}</span>
          <svg
            width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"
            className={`transition-transform duration-200 ${expanded ? "rotate-180" : ""}`}
          >
            <polyline points="6 9 12 15 18 9" />
          </svg>
        </div>
      </button>

      {/* Evidence panel */}
      {expanded && evidence.length > 0 && (
        <div className="px-4 pb-4 pt-0 ml-9">
          <div className="border-t border-slate-200/50 pt-3">
            <EvidenceChain evidence={evidence} />
          </div>
        </div>
      )}
    </div>
  );
}

function Tag({ children }: { children: React.ReactNode }) {
  return (
    <span className="inline-block px-2 py-0.5 rounded text-[10px] font-medium bg-white/70 text-slate-500 border border-slate-100">
      {children}
    </span>
  );
}
