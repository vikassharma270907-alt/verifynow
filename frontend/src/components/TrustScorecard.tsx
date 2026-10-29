import type { VerificationReport } from "../hooks/useVerification";

interface Props {
  report: VerificationReport;
}

const riskColors: Record<string, string> = {
  low: "text-green-700 bg-green-50 border-green-200",
  medium: "text-yellow-700 bg-yellow-50 border-yellow-200",
  high: "text-orange-700 bg-orange-50 border-orange-200",
  critical: "text-red-700 bg-red-50 border-red-200",
};

const scoreColor = (score: number) => {
  if (score >= 75) return "text-green-600";
  if (score >= 50) return "text-yellow-600";
  if (score >= 30) return "text-orange-600";
  return "text-red-600";
};

export default function TrustScorecard({ report }: Props) {
  return (
    <div className="bg-white rounded-xl border border-gray-200 p-6">
      <div className="flex items-start justify-between mb-6">
        <div>
          <h3 className="text-lg font-bold text-gray-900">Evidence Trust Scorecard</h3>
          <p className="text-sm text-gray-500 mt-0.5">
            {report.document_name} · {report.document_type.replace(/_/g, " ")}
          </p>
        </div>
        <div className={`px-3 py-1 rounded-full text-sm font-semibold border ${riskColors[report.risk_level] ?? riskColors.medium}`}>
          {report.risk_level.toUpperCase()} RISK
        </div>
      </div>

      {/* Score + Counts */}
      <div className="grid grid-cols-4 gap-4 text-center">
        <div className="bg-gray-50 rounded-lg p-4">
          <div className={`text-3xl font-bold ${scoreColor(report.trust_score)}`}>
            {report.trust_score.toFixed(0)}%
          </div>
          <div className="text-xs text-gray-500 mt-1">Trust Score</div>
        </div>
        <div className="bg-gray-50 rounded-lg p-4">
          <div className="text-3xl font-bold text-green-600">{report.verified_count}</div>
          <div className="text-xs text-gray-500 mt-1">✅ Verified</div>
        </div>
        <div className="bg-gray-50 rounded-lg p-4">
          <div className="text-3xl font-bold text-gray-400">{report.unverifiable_count}</div>
          <div className="text-xs text-gray-500 mt-1">⚠️ Unverifiable</div>
        </div>
        <div className="bg-gray-50 rounded-lg p-4">
          <div className="text-3xl font-bold text-red-600">{report.contradicted_count}</div>
          <div className="text-xs text-gray-500 mt-1">❌ Contradicted</div>
        </div>
      </div>
    </div>
  );
}
