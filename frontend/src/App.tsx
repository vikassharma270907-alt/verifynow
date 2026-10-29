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
    <div className="min-h-screen bg-[var(--color-surface)]">
      {/* Header */}
      <header className="glass-card sticky top-0 z-50 px-6 py-3">
        <div className="max-w-4xl mx-auto flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-[var(--color-brand)] flex items-center justify-center">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2.5">
                <polyline points="20 6 9 17 4 12" />
              </svg>
            </div>
            <div>
              <h1 className="text-base font-bold text-slate-900 leading-none">
                Verify<span className="text-[var(--color-brand)]">Flow</span>
              </h1>
              <p className="text-[10px] text-slate-400 mt-0.5">
                The model thinks. The evidence decides.
              </p>
            </div>
          </div>
          <nav className="flex gap-1 bg-slate-100 rounded-lg p-0.5">
            <button
              onClick={() => { setTab("verify"); reset(); }}
              className={`px-3 py-1.5 rounded-md text-xs font-medium transition-all ${
                tab === "verify"
                  ? "bg-white text-slate-900 shadow-sm"
                  : "text-slate-500 hover:text-slate-700"
              }`}
            >
              Verify
            </button>
            <button
              onClick={() => { setTab("challenge"); reset(); }}
              className={`px-3 py-1.5 rounded-md text-xs font-medium transition-all ${
                tab === "challenge"
                  ? "bg-white text-slate-900 shadow-sm"
                  : "text-slate-500 hover:text-slate-700"
              }`}
            >
              ⚔️ Challenge
            </button>
          </nav>
        </div>
      </header>

      {/* Main */}
      <main className="max-w-4xl mx-auto px-6 py-8">
        {error && (
          <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-xl text-sm text-red-700 flex items-center gap-2">
            <span className="shrink-0 w-5 h-5 rounded-full bg-red-100 flex items-center justify-center text-xs font-bold text-red-600">!</span>
            {error}
          </div>
        )}

        {!report && !loading && (
          tab === "verify" ? <DropZone onFileDrop={verifyFile} /> : <ChallengeMode onRun={handleChallenge} />
        )}

        {loading && <LoadingPipeline />}

        {report && (
          <div className="space-y-5">
            <div className="flex items-center justify-between">
              <h2 className="text-lg font-bold text-slate-900">Verification Results</h2>
              <button onClick={reset} className="inline-flex items-center gap-1 px-3 py-1.5 text-xs font-medium text-slate-600 bg-white border border-slate-200 rounded-lg hover:bg-slate-50 transition-colors">
                <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><polyline points="15 18 9 12 15 6" /></svg>
                New verification
              </button>
            </div>

            <TrustScorecard report={report} />

            <div className="glass-card rounded-2xl p-5">
              <h3 className="text-sm font-semibold text-slate-800 mb-2">Summary</h3>
              <p className="text-sm text-slate-600 leading-relaxed whitespace-pre-line">{report.summary}</p>
            </div>

            <div>
              <h3 className="text-sm font-semibold text-slate-800 mb-3">
                Claims <span className="text-slate-400 font-normal">({report.total_claims})</span>
              </h3>
              <div className="space-y-2">
                {report.claim_verifications.map((cv) => (
                  <ClaimCard key={cv.claim.id} verification={cv} />
                ))}
              </div>
            </div>

            <div className="flex flex-wrap gap-3 text-[11px] text-slate-400 bg-slate-50 rounded-xl px-4 py-3">
              <span>⚡ Nano: <strong className="text-slate-600">{report.model_tier_usage.nano?.toLocaleString() ?? 0}</strong> tokens</span>
              <span>🧠 Super: <strong className="text-slate-600">{report.model_tier_usage.super?.toLocaleString() ?? 0}</strong> tokens</span>
              <span>📋 Ultra: <strong className="text-slate-600">{report.model_tier_usage.ultra?.toLocaleString() ?? 0}</strong> tokens</span>
              <span className="ml-auto">⏱ {(report.processing_time_ms / 1000).toFixed(1)}s</span>
            </div>
          </div>
        )}
      </main>

      <footer className="border-t border-slate-100 mt-16 py-5 text-center text-[11px] text-slate-400">
        NVIDIA Nemotron on Nebius Token Factory · Tavily Live Search · Deterministic Verification
      </footer>
    </div>
  );
}
