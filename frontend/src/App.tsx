import { useState } from "react";
import { useVerification, type Challenge } from "./hooks/useVerification";
import DropZone from "./components/DropZone";
import TrustScorecard from "./components/TrustScorecard";
import ClaimCard from "./components/ClaimCard";
import ChallengeMode from "./components/ChallengeMode";

export default function App() {
  const { report, loading, error, verifyFile, verifyText, reset } = useVerification();
  const [tab, setTab] = useState<"verify" | "challenge">("verify");

  const handleChallenge = (challenge: Challenge) => {
    if (challenge.document_text) {
      verifyText(challenge.document_text, `challenge-${challenge.id}.txt`);
    }
  };

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white border-b border-gray-200 px-6 py-4">
        <div className="max-w-5xl mx-auto flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">
              Verify<span className="text-blue-600">Flow</span>
            </h1>
            <p className="text-sm text-gray-500 mt-0.5">
              The model thinks. The evidence decides.
            </p>
          </div>
          <div className="flex gap-2">
            <button
              onClick={() => { setTab("verify"); reset(); }}
              className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                tab === "verify"
                  ? "bg-blue-600 text-white"
                  : "bg-gray-100 text-gray-700 hover:bg-gray-200"
              }`}
            >
              Verify Document
            </button>
            <button
              onClick={() => { setTab("challenge"); reset(); }}
              className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                tab === "challenge"
                  ? "bg-red-600 text-white"
                  : "bg-gray-100 text-gray-700 hover:bg-gray-200"
              }`}
            >
              ⚔️ Challenge Mode
            </button>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-5xl mx-auto px-6 py-8">
        {/* Error Banner */}
        {error && (
          <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-lg text-red-700">
            <strong>Error:</strong> {error}
          </div>
        )}

        {/* Upload / Challenge */}
        {!report && !loading && (
          tab === "verify" ? (
            <DropZone onFileDrop={verifyFile} />
          ) : (
            <ChallengeMode onRun={handleChallenge} />
          )
        )}

        {/* Loading */}
        {loading && (
          <div className="text-center py-20">
            <div className="inline-block w-12 h-12 border-4 border-blue-200 border-t-blue-600 rounded-full animate-spin" />
            <p className="mt-4 text-gray-600 font-medium">
              Extracting claims → Searching evidence → Verifying...
            </p>
            <p className="mt-1 text-sm text-gray-400">
              Nano extracts · Tavily searches · Super analyzes · Code verifies · Ultra summarizes
            </p>
          </div>
        )}

        {/* Results */}
        {report && (
          <div className="space-y-6">
            <div className="flex items-center justify-between">
              <h2 className="text-xl font-bold">Verification Results</h2>
              <button
                onClick={reset}
                className="px-4 py-2 text-sm bg-gray-100 hover:bg-gray-200 rounded-lg transition-colors"
              >
                ← Verify Another
              </button>
            </div>

            <TrustScorecard report={report} />

            {/* Summary */}
            <div className="bg-white rounded-xl border border-gray-200 p-6">
              <h3 className="font-semibold text-gray-900 mb-2">Summary</h3>
              <p className="text-gray-700 leading-relaxed whitespace-pre-line">
                {report.summary}
              </p>
            </div>

            {/* Claims */}
            <div>
              <h3 className="font-semibold text-gray-900 mb-3">
                Claims ({report.total_claims})
              </h3>
              <div className="space-y-3">
                {report.claim_verifications.map((cv) => (
                  <ClaimCard key={cv.claim.id} verification={cv} />
                ))}
              </div>
            </div>

            {/* Model Usage */}
            <div className="bg-gray-100 rounded-xl p-4 text-sm text-gray-600">
              <span className="font-medium">Model tier usage:</span>{" "}
              Nano: {report.model_tier_usage.nano?.toLocaleString() ?? 0} tokens ·{" "}
              Super: {report.model_tier_usage.super?.toLocaleString() ?? 0} tokens ·{" "}
              Ultra: {report.model_tier_usage.ultra?.toLocaleString() ?? 0} tokens ·{" "}
              Processed in {(report.processing_time_ms / 1000).toFixed(1)}s
            </div>
          </div>
        )}
      </main>

      {/* Footer */}
      <footer className="border-t border-gray-200 mt-12 py-6 text-center text-sm text-gray-400">
        Powered by NVIDIA Nemotron on Nebius Token Factory · Tavily Live Search · Deterministic Verification
      </footer>
    </div>
  );
}
