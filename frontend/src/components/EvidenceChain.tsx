import type { Evidence } from "../hooks/useVerification";

interface Props { evidence: Evidence[] }

function host(url: string) { try { return new URL(url).hostname; } catch { return url; } }

export default function EvidenceChain({ evidence }: Props) {
  return (
    <div className="space-y-2">
      {evidence.map((ev, i) => (
        <div key={i} className="rounded-md border p-3 text-xs"
          style={{
            background: ev.supports_claim ? "var(--verified-soft)" : "var(--contradicted-soft)",
            borderColor: ev.supports_claim ? "#D1FAE5" : "#FECACA",
          }}>
          <div className="flex items-center gap-2 mb-1">
            <span className="font-semibold text-[10px] px-1.5 py-0.5 rounded"
              style={{
                background: ev.supports_claim ? "#D1FAE5" : "#FECACA",
                color: ev.supports_claim ? "var(--verified)" : "var(--contradicted)",
              }}>
              {ev.supports_claim ? "SUPPORTS" : "CONTRADICTS"}
            </span>
            <span className="text-[10px] px-1.5 py-0.5 rounded" style={{ background: "#F3F4F6", color: "var(--text-tertiary)" }}>
              {ev.source_type.replace("_", " ")}
            </span>
            <span className="ml-auto" style={{ color: "var(--text-tertiary)" }}>
              {(ev.relevance_score * 100).toFixed(0)}%
            </span>
          </div>
          <p className="leading-relaxed" style={{ color: "var(--text-secondary)" }}>{ev.content}</p>
          {ev.source_url && (
            <a href={ev.source_url} target="_blank" rel="noopener noreferrer"
              className="inline-block mt-1 hover:underline" style={{ color: "var(--brand)" }}>
              {ev.source_title || host(ev.source_url)}
            </a>
          )}
        </div>
      ))}
    </div>
  );
}
