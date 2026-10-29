import type { Evidence } from "../hooks/useVerification";

interface Props {
  evidence: Evidence[];
}

export default function EvidenceChain({ evidence }: Props) {
  return (
    <div className="space-y-2">
      {evidence.map((ev, i) => (
        <div
          key={i}
          className={`rounded-lg p-3 text-sm ${
            ev.supports_claim
              ? "bg-green-50 border border-green-100"
              : "bg-red-50 border border-red-100"
          }`}
        >
          <div className="flex items-center gap-2 mb-1">
            <span className="text-xs font-mono px-1.5 py-0.5 rounded bg-white/60">
              {ev.source_type}
            </span>
            <span className={`text-xs font-semibold ${ev.supports_claim ? "text-green-700" : "text-red-700"}`}>
              {ev.supports_claim ? "SUPPORTS" : "CONTRADICTS"}
            </span>
            <span className="text-xs text-gray-400 ml-auto">
              relevance: {(ev.relevance_score * 100).toFixed(0)}%
            </span>
          </div>
          <p className="text-gray-700 leading-relaxed">{ev.content}</p>
          {ev.source_url && (
            <a
              href={ev.source_url}
              target="_blank"
              rel="noopener noreferrer"
              className="text-xs text-blue-600 hover:underline mt-1 inline-block"
            >
              {ev.source_title || ev.source_url}
            </a>
          )}
        </div>
      ))}
    </div>
  );
}
