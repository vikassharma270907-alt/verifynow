import { useState } from "react";
import { useVerification, type Challenge } from "./hooks/useVerification";
import DropZone from "./components/DropZone";
import TrustScorecard from "./components/TrustScorecard";
import ClaimCard from "./components/ClaimCard";
import ChallengeMode from "./components/ChallengeMode";
import LoadingPipeline from "./components/LoadingPipeline";

export default function App() {
  const { report, loading, error, verifyFile, verifyText, reset } = useVerification();
  const [tab, setTab] = useState<"verify" | "challenge">("verify");

  const handleChallenge = (challenge: Challenge) => {
    if (challenge.document_text) {
      verifyText(challenge.document_text, `challenge-${challenge.id}.txt`);
    }
  };

  return (
    <div className="min-h-screen" style={{ background: "var(--surface)" }}>
      {/* ─── Header ─── */}
      <header className="border-b" style={{ borderColor: "var(--border)", background: "var(--card)" }}>
        <div className="max-w-[720px] mx-auto px-3 sm:px-5 h-14 flex items-center justify-between">
          <a href="/" className="flex items-center gap-2 sm:gap-2.5 no-underline">
            <div className="w-7 h-7 rounded-md flex items-center justify-center" style={{ background: "var(--brand)" }}>
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="3"><polyline points="20 6 9 17 4 12" /></svg>
            </div>
            <span className="text-[14px] sm:text-[15px] font-bold" style={{ color: "var(--text-primary)", fontFamily: "'DM Sans', system-ui" }}>
              VerifyFlow
            </span>
          </a>

          <div className="flex items-center gap-1 p-0.5 rounded-md" style={{ background: "var(--surface)" }}>
            {(["verify", "challenge"] as const).map((t) => (
              <button
                key={t}
                onClick={() => { setTab(t); reset(); }}
                className="px-2.5 sm:px-3 py-1 rounded text-[12px] sm:text-[13px] font-medium transition-colors"
                style={{
                  background: tab === t ? "var(--card)" : "transparent",
                  color: tab === t ? "var(--text-primary)" : "var(--text-secondary)",
                  boxShadow: tab === t ? "0 1px 2px rgba(0,0,0,0.06)" : "none",
                }}
              >
                {t === "verify" ? "Verify" : "⚔ Challenge"}
              </button>
            ))}
          </div>
        </div>
      </header>

      {/* ─── Main ─── */}
      <main className="max-w-[720px] mx-auto px-3 sm:px-5 py-6 sm:py-10">
        {/* Error */}
        {error && (
          <div className="mb-8 px-4 py-3 rounded-lg text-sm flex items-start gap-2" style={{ background: "var(--contradicted-soft)", color: "var(--contradicted)" }}>
            <span className="font-bold mt-px">✕</span>
            <span>{error}</span>
          </div>
        )}

        {/* States */}
        {!report && !loading && (
          tab === "verify" ? <DropZone onFileDrop={verifyFile} /> : <ChallengeMode onRun={handleChallenge} />
        )}

        {loading && <LoadingPipeline />}

        {report && (
          <div className="space-y-8">
            {/* Title row */}
            <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
              <h2 className="text-lg sm:text-xl font-bold">Results</h2>
              <button
                onClick={reset}
                className="text-[13px] font-medium px-3 py-1.5 rounded-md border transition-colors hover:bg-gray-50 self-start sm:self-auto"
                style={{ borderColor: "var(--border)", color: "var(--text-secondary)" }}
              >
                ← New verification
              </button>
            </div>

            <TrustScorecard report={report} />

            {/* Summary */}
            <section>
              <h3 className="text-sm font-semibold mb-2" style={{ color: "var(--text-primary)" }}>Summary</h3>
              <div className="rounded-lg border p-5" style={{ background: "var(--card)", borderColor: "var(--border)" }}>
                <p className="text-[15px] leading-relaxed whitespace-pre-line" style={{ color: "var(--text-secondary)" }}>
                  {report.summary}
                </p>
              </div>
            </section>

            {/* Claims */}
            <section>
              <h3 className="text-sm font-semibold mb-3" style={{ color: "var(--text-primary)" }}>
                Claims
                <span className="font-normal ml-1.5" style={{ color: "var(--text-tertiary)" }}>
                  {report.total_claims}
                </span>
              </h3>
              <div className="space-y-2">
                {report.claim_verifications.map((cv) => (
                  <ClaimCard key={cv.claim.id} verification={cv} />
                ))}
              </div>
            </section>

            {/* Telemetry */}
            <div className="flex flex-wrap gap-x-3 sm:gap-x-5 gap-y-1 text-[10px] sm:text-xs py-3 px-3 sm:px-4 rounded-lg" style={{ background: "var(--surface)", color: "var(--text-tertiary)" }}>
              <span>Nano <b style={{ color: "var(--text-secondary)" }}>{(report.model_tier_usage.nano ?? 0).toLocaleString()}</b> tok</span>
              <span>Super <b style={{ color: "var(--text-secondary)" }}>{(report.model_tier_usage.super ?? 0).toLocaleString()}</b> tok</span>
              <span>Ultra <b style={{ color: "var(--text-secondary)" }}>{(report.model_tier_usage.ultra ?? 0).toLocaleString()}</b> tok</span>
              <span className="ml-auto">{(report.processing_time_ms / 1000).toFixed(1)}s</span>
            </div>
          </div>
        )}
      </main>

      {/* ─── Footer ─── */}
      <footer className="mt-12 sm:mt-20 py-4 sm:py-6 text-center text-[10px] sm:text-xs border-t" style={{ borderColor: "var(--border)", color: "var(--text-tertiary)" }}>
        Powered by NVIDIA Nemotron on Nebius Token Factory
      </footer>
    </div>
  );
}
