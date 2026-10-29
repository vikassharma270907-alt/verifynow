import type { Evidence } from "../hooks/useVerification";

interface Props { evidence: Evidence[] }

function host(url: string) { try { return new URL(url).hostname; } catch { return url; } }

const STANCE: Record<Evidence["stance"], { label: string; color: string; soft: string; note?: string }> = {
  supports: { label: "SUPPORTS", color: "var(--verified)", soft: "var(--verified-soft)" },
  contradicts: { label: "CONTRADICTS", color: "var(--contradicted)", soft: "var(--contradicted-soft)" },
  irrelevant: { label: "NOT RELEVANT", color: "var(--text-tertiary)", soft: "transparent" },
  rejected: {
    label: "REJECTED",
    color: "var(--unverifiable)",
    soft: "transparent",
    note: "A model proposed a verdict, but its quote or entity check failed, so it was ignored.",
  },
  unjudged: { label: "NOT ASSESSED", color: "var(--text-tertiary)", soft: "transparent" },
};

export default function EvidenceChain({ evidence }: Props) {
  return (
    <div className="space-y-2">
      {evidence.map((ev, i) => {
        const s = STANCE[ev.stance] ?? STANCE.unjudged;
        return (
          <div key={i} className="rounded-md border p-3 text-xs"
            style={{ background: s.soft, borderColor: "var(--border)" }}>
            <div className="flex items-center gap-2 mb-1">
              <span className="font-semibold text-[10px] px-1.5 py-0.5 rounded"
                style={{ color: s.color, border: `1px solid ${s.color}` }}>
                {s.label}
              </span>
              <span className="ml-auto" style={{ color: "var(--text-tertiary)" }}>
                relevance {(ev.relevance_score * 100).toFixed(0)}%
              </span>
            </div>
            {ev.quote && (ev.stance === "supports" || ev.stance === "contradicts") && (
              <blockquote className="mb-1 pl-2 border-l-2 italic" style={{ borderColor: s.color, color: "var(--text-primary)" }}>
                “{ev.quote}”
              </blockquote>
            )}
            {s.note && <p className="mb-1" style={{ color: s.color }}>{s.note}</p>}
            <p className="leading-relaxed" style={{ color: "var(--text-secondary)" }}>{ev.content}</p>
            {ev.source_url && (
              <a href={ev.source_url} target="_blank" rel="noopener noreferrer"
                className="inline-block mt-1 hover:underline max-w-full truncate" style={{ color: "var(--brand)" }}>
                {ev.source_title || host(ev.source_url)}
              </a>
            )}
          </div>
        );
      })}
    </div>
  );
}
