import type { Evidence } from "../hooks/useVerification";

interface Props {
  evidence: Evidence[];
}

function safeHostname(url: string): string {
  try { return new URL(url).hostname; } catch { return url; }
}

export default function EvidenceChain({ evidence }: Props) {
  return (
    <div className="space-y-2">
      {evidence.map((ev, i) => {
        const supports = ev.supports_claim;
        return (
          <div key={i} className={`rounded-lg p-3 text-xs border ${supports ? "bg-emerald-50/50 border-emerald-100" : "bg-red-50/50 border-red-100"}`}>
            <div className="flex items-center gap-2 mb-1.5">
              <span className={`inline-flex items-center gap-1 px-1.5 py-0.5 rounded font-semibold text-[10px] ${supports ? "bg-emerald-100 text-emerald-700" : "bg-red-100 text-red-700"}`}>
                {supports ? "▲ SUPPORTS" : "▼ CONTRADICTS"}
              </span>
              <span className="px-1.5 py-0.5 rounded bg-slate-100 text-slate-500 font-mono text-[10px]">
                {ev.source_type.replace("_", " ")}
              </span>
              <span className="ml-auto text-slate-400">{(ev.relevance_score * 100).toFixed(0)}% match</span>
            </div>
            <p className="text-slate-600 leading-relaxed line-clamp-3">{ev.content}</p>
            {ev.source_url && (
              <a href={ev.source_url} target="_blank" rel="noopener noreferrer" className="inline-flex items-center gap-1 mt-1.5 text-[var(--color-brand)] hover:underline">
                {ev.source_title || safeHostname(ev.source_url)}
              </a>
            )}
          </div>
        );
      })}
    </div>
  );
}
