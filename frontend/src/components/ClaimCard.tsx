import { useState } from "react";
import type { ClaimVerification } from "../hooks/useVerification";
import EvidenceChain from "./EvidenceChain";

interface Props {
  verification: ClaimVerification;
}

const statusIcons: Record<string, string> = {
  verified: "✅",
  unverifiable: "⚠️",
  contradicted: "❌",
  pending: "⏳",
  rejected: "🚫",
};

const statusColors: Record<string, string> = {
  verified: "border-green-200 bg-green-50",
  unverifiable: "border-yellow-200 bg-yellow-50",
  contradicted: "border-red-200 bg-red-50",
  pending: "border-gray-200 bg-gray-50",
  rejected: "border-red-300 bg-red-100",
};

export default function ClaimCard({ verification }: Props) {
  const [expanded, setExpanded] = useState(false);
  const { claim, evidence, verdict } = verification;

  return (
    <div className={`rounded-xl border p-4 transition-all ${statusColors[verdict] ?? "border-gray-200 bg-white"}`}>
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full text-left flex items-start gap-3"
        aria-expanded={expanded}
      >
        <span className="text-lg shrink-0 mt-0.5">
          {statusIcons[verdict] ?? "❓"}
        </span>
        <div className="flex-1 min-w-0">
          <p className="font-medium text-gray-900">{claim.text}</p>
          <div className="flex flex-wrap gap-2 mt-1 text-xs text-gray-500">
            <span className="bg-white/60 px-2 py-0.5 rounded">{claim.category}</span>
            <span className="bg-white/60 px-2 py-0.5 rounded">{claim.source_location}</span>
            <span className="bg-white/60 px-2 py-0.5 rounded">
              confidence: {(claim.confidence * 100).toFixed(0)}%
            </span>
          </div>
          {claim.verification_reason && (
            <p className="text-sm text-gray-600 mt-1">{claim.verification_reason}</p>
          )}
        </div>
        <span className="text-gray-400 shrink-0 text-sm mt-1">
          {expanded ? "▲" : "▼"} {evidence.length} source{evidence.length !== 1 ? "s" : ""}
        </span>
      </button>

      {expanded && evidence.length > 0 && (
        <div className="mt-3 ml-8 border-t border-gray-200 pt-3">
          <EvidenceChain evidence={evidence} />
        </div>
      )}
    </div>
  );
}
