import { useState, useEffect } from "react";

const STEPS = [
  { label: "Extracting claims",    detail: "Nemotron Nano", color: "var(--brand)" },
  { label: "Searching evidence",   detail: "Tavily Search", color: "var(--unverifiable)" },
  { label: "Analyzing conflicts",  detail: "Nemotron Super", color: "#8B5CF6" },
  { label: "Verifying claims",     detail: "Code verifier", color: "var(--verified)" },
  { label: "Writing summary",      detail: "Nemotron Ultra", color: "var(--contradicted)" },
];

export default function LoadingPipeline() {
  const [active, setActive] = useState(0);
  useEffect(() => {
    const t = setInterval(() => setActive(p => Math.min(p + 1, STEPS.length - 1)), 5500);
    return () => clearInterval(t);
  }, []);

  return (
    <div className="max-w-sm mx-auto py-10 sm:py-16 space-y-10">
      <div className="text-center space-y-2">
        <div className="mx-auto w-8 h-8 border-[3px] rounded-full animate-spin"
          style={{ borderColor: "var(--border)", borderTopColor: "var(--brand)" }} />
        <p className="text-sm font-medium" style={{ color: "var(--text-primary)" }}>Verifying document</p>
      </div>
      <div className="space-y-1">
        {STEPS.map((s, i) => {
          const done = i < active, now = i === active, later = i > active;
          return (
            <div key={i} className="step-enter flex items-center gap-3 rounded-lg px-3 py-2.5"
              style={{ background: now ? `${s.color}08` : "transparent" }}>
              <div className="w-6 h-6 rounded flex items-center justify-center text-xs shrink-0"
                style={{ background: done ? "var(--verified-soft)" : now ? `${s.color}18` : "var(--surface)" }}>
                {done ? (
                  <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="var(--verified)" strokeWidth="3"><polyline points="20 6 9 17 4 12" /></svg>
                ) : (
                  <span className="w-2 h-2 rounded-full" style={{ background: later ? "var(--border)" : s.color, opacity: later ? 0.5 : 1 }} />
                )}
              </div>
              <div className="flex-1">
                <p className="text-sm font-medium" style={{ color: done ? "var(--verified)" : now ? s.color : "var(--text-tertiary)" }}>{s.label}</p>
                <p className="text-[11px]" style={{ color: done ? "var(--verified)" : "var(--text-tertiary)", opacity: later ? 0.4 : 0.7 }}>{s.detail}</p>
              </div>
              {now && <span className="w-1.5 h-1.5 rounded-full active-pulse shrink-0" style={{ background: s.color }} />}
            </div>
          );
        })}
      </div>
    </div>
  );
}
