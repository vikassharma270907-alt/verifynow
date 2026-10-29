import type { DocumentFinding } from "../hooks/useVerification";

interface Props { findings: DocumentFinding[]; notes: string[] }

const TITLES: Record<string, string> = {
  HOMOGRAPH_DOMAIN: "Look-alike domain",
  PUNYCODE_DOMAIN: "Punycode domain",
  PROMPT_INJECTION: "Prompt injection",
  INVALID_DATE: "Impossible date",
  INTERNAL_CONFLICT: "Conflicting statements",
  UNRECOGNIZED_AUTHORITY: "Unrecognized authority",
};

export default function FindingsPanel({ findings, notes }: Props) {
  if (findings.length === 0 && notes.length === 0) return null;

  return (
    <section aria-labelledby="findings-heading">
      <h3 id="findings-heading" className="text-sm font-semibold mb-3" style={{ color: "var(--text-primary)" }}>
        Findings
        <span className="font-normal ml-1.5" style={{ color: "var(--text-tertiary)" }}>{findings.length}</span>
      </h3>

      <ul className="space-y-2">
        {findings.map((f, i) => {
          const high = f.severity === "HIGH";
          const color = high ? "var(--contradicted)" : "var(--unverifiable)";
          return (
            <li key={i} className="rounded-lg border p-3 sm:p-4"
              style={{ background: "var(--card)", borderColor: "var(--border)", borderLeft: `3px solid ${color}` }}>
              <div className="flex items-center gap-2 mb-1.5">
                <span className="text-[10px] font-semibold px-1.5 py-0.5 rounded" style={{ color, border: `1px solid ${color}` }}>
                  {f.severity}
                </span>
                <span className="text-[13px] font-semibold" style={{ color: "var(--text-primary)" }}>
                  {TITLES[f.kind] ?? f.kind}
                </span>
              </div>
              <p className="text-[12px] font-mono break-all mb-1.5 px-2 py-1 rounded"
                style={{ background: "var(--surface)", color: "var(--text-primary)" }}>
                {f.quote}
              </p>
              <p className="text-[13px] leading-relaxed" style={{ color: "var(--text-secondary)" }}>{f.explanation}</p>
            </li>
          );
        })}
      </ul>

      {notes.length > 0 && (
        <ul className="mt-3 space-y-1" aria-label="Analysis limitations">
          {notes.map((n, i) => (
            <li key={i} className="text-[12px] px-3 py-2 rounded-md"
              style={{ background: "var(--unverifiable-soft)", color: "var(--unverifiable)" }}>
              {n}
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
