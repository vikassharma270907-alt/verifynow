import { useState } from "react";
import type { VerificationReport } from "../hooks/useVerification";

interface Baseline {
  verdict: "TRUSTWORTHY" | "SUSPICIOUS" | "UNKNOWN";
  confidence: number | null;
  reasoning: string;
  model: string;
}

interface Props { file: File | null; report: VerificationReport }

function outcome(b: Baseline, risk: string): { text: string; tone: "bad" | "ok" | "neutral" } {
  const flagged = risk === "high" || risk === "critical";
  if (b.verdict === "TRUSTWORTHY" && flagged)
    return { text: `The plain LLM called this document trustworthy. VerifyFlow rated it ${risk} risk and shows the evidence.`, tone: "bad" };
  if (b.verdict === "SUSPICIOUS" && flagged)
    return { text: "Both flagged this document. VerifyFlow also shows exactly what it found, with the quotes that back it up.", tone: "ok" };
  if (b.verdict === "SUSPICIOUS")
    return { text: "The plain LLM was suspicious. VerifyFlow found no deterministic issues or contradictions.", tone: "neutral" };
  if (b.verdict === "TRUSTWORTHY")
    return { text: "Both treated this document as acceptable.", tone: "ok" };
  return { text: "The plain LLM gave no clear verdict.", tone: "neutral" };
}

export default function ComparisonPanel({ file, report }: Props) {
  const [loading, setLoading] = useState(false);
  const [baseline, setBaseline] = useState<Baseline | null>(null);
  const [error, setError] = useState<string | null>(null);

  if (!file) return null;

  const run = async () => {
    setLoading(true);
    setError(null);
    try {
      const form = new FormData();
      form.append("file", file);
      const resp = await fetch("/api/baseline", { method: "POST", body: form });
      if (!resp.ok) {
        const body = await resp.json().catch(() => ({ detail: resp.statusText }));
        throw new Error(body.detail || `HTTP ${resp.status}`);
      }
      setBaseline(await resp.json());
    } catch (err) {
      setError(err instanceof Error ? err.message : "Comparison failed");
    } finally {
      setLoading(false);
    }
  };

  const result = baseline ? outcome(baseline, report.risk_level) : null;
  const toneColor = result?.tone === "bad" ? "var(--contradicted)" : result?.tone === "ok" ? "var(--verified)" : "var(--text-secondary)";
  const bVerdictColor = baseline?.verdict === "SUSPICIOUS" ? "var(--unverifiable)" : baseline?.verdict === "TRUSTWORTHY" ? "var(--verified)" : "var(--text-tertiary)";
  const riskColor = report.risk_level === "low" ? "var(--verified)" : report.risk_level === "medium" ? "var(--unverifiable)" : "var(--contradicted)";

  return (
    <section aria-labelledby="compare-heading">
      <h3 id="compare-heading" className="text-sm font-semibold mb-2" style={{ color: "var(--text-primary)" }}>
        Compare with a plain LLM
      </h3>

      {!baseline && (
        <div className="rounded-lg border p-3 sm:p-5 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between"
          style={{ background: "var(--card)", borderColor: "var(--border)" }}>
          <p className="text-[13px] leading-relaxed" style={{ color: "var(--text-secondary)" }}>
            Send this same document to one Nemotron Ultra call with a normal “is this trustworthy?” prompt and no evidence checks, to see what it says.
          </p>
          <button onClick={run} disabled={loading}
            className="shrink-0 text-[13px] font-medium px-3 py-1.5 rounded-md border transition-colors disabled:opacity-50"
            style={{ borderColor: "var(--border)", color: "var(--text-primary)" }}>
            {loading ? "Asking…" : "Run comparison"}
          </button>
        </div>
      )}

      {error && (
        <p role="alert" className="mt-2 text-[12px] px-3 py-2 rounded-md"
          style={{ background: "var(--contradicted-soft)", color: "var(--contradicted)" }}>{error}</p>
      )}

      <div aria-live="polite">
        {baseline && result && (
          <div className="space-y-3">
            <div className="grid gap-2 sm:grid-cols-2">
              <div className="rounded-lg border p-3 sm:p-4" style={{ background: "var(--card)", borderColor: "var(--border)" }}>
                <p className="text-[11px] uppercase tracking-wide mb-2" style={{ color: "var(--text-tertiary)" }}>
                  Plain LLM, no evidence checks
                </p>
                <p className="text-[18px] font-bold" style={{ color: bVerdictColor }}>
                  {baseline.verdict}
                  {baseline.confidence !== null && (
                    <span className="text-[12px] font-normal ml-2" style={{ color: "var(--text-tertiary)" }}>{baseline.confidence}% confident</span>
                  )}
                </p>
                <p className="text-[13px] leading-relaxed mt-2" style={{ color: "var(--text-secondary)" }}>{baseline.reasoning}</p>
              </div>

              <div className="rounded-lg border p-3 sm:p-4" style={{ background: "var(--card)", borderColor: "var(--border)" }}>
                <p className="text-[11px] uppercase tracking-wide mb-2" style={{ color: "var(--text-tertiary)" }}>
                  VerifyFlow, evidence decides
                </p>
                <p className="text-[18px] font-bold" style={{ color: riskColor }}>
                  {report.risk_level.toUpperCase()} RISK
                  <span className="text-[12px] font-normal ml-2" style={{ color: "var(--text-tertiary)" }}>trust {report.trust_score}</span>
                </p>
                <p className="text-[13px] leading-relaxed mt-2" style={{ color: "var(--text-secondary)" }}>
                  {report.findings.length} finding{report.findings.length === 1 ? "" : "s"}, {report.contradicted_count} contradicted claim{report.contradicted_count === 1 ? "" : "s"}, each with the quote or rule behind it.
                </p>
              </div>
            </div>

            <p className="text-[13px] font-medium px-1" style={{ color: toneColor }}>{result.text}</p>
            <p className="text-[11px] px-1" style={{ color: "var(--text-tertiary)" }}>
              One call to {baseline.model}. The model can vary between runs.
            </p>
          </div>
        )}
      </div>
    </section>
  );
}
