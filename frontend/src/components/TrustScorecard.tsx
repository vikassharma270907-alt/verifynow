import type { VerificationReport } from "../hooks/useVerification";

interface Props {
  report: VerificationReport;
}

const riskConfig: Record<string, { label: string; bg: string; text: string; border: string; dot: string }> = {
  low:      { label: "LOW RISK",      bg: "bg-emerald-50",  text: "text-emerald-700",  border: "border-emerald-200", dot: "bg-emerald-500" },
  medium:   { label: "MEDIUM RISK",   bg: "bg-amber-50",    text: "text-amber-700",    border: "border-amber-200",   dot: "bg-amber-500" },
  high:     { label: "HIGH RISK",     bg: "bg-orange-50",   text: "text-orange-700",   border: "border-orange-200",  dot: "bg-orange-500" },
  critical: { label: "CRITICAL RISK", bg: "bg-red-50",      text: "text-red-700",      border: "border-red-200",     dot: "bg-red-500" },
};

function scoreColor(score: number) {
  if (score >= 75) return "#059669";
  if (score >= 50) return "#d97706";
  if (score >= 30) return "#ea580c";
  return "#dc2626";
}

function ScoreRing({ score }: { score: number }) {
  const radius = 44;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference - (score / 100) * circumference;
  const color = scoreColor(score);

  return (
    <div className="relative w-28 h-28 shrink-0">
      <svg viewBox="0 0 100 100" className="w-full h-full -rotate-90">
        <circle cx="50" cy="50" r={radius} fill="none" stroke="#f1f5f9" strokeWidth="8" />
        <circle
          cx="50" cy="50" r={radius}
          fill="none"
          stroke={color}
          strokeWidth="8"
          strokeLinecap="round"
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          className="score-ring"
          style={{ "--target-offset": offset } as React.CSSProperties}
        />
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <span className="text-2xl font-bold" style={{ color }}>{score.toFixed(0)}</span>
        <span className="text-[10px] font-medium text-slate-400 uppercase tracking-wider">Trust</span>
      </div>
    </div>
  );
}

export default function TrustScorecard({ report }: Props) {
  const risk = riskConfig[report.risk_level] ?? riskConfig.medium;

  return (
    <div className="glass-card rounded-2xl p-6 space-y-5">
      {/* Header row */}
      <div className="flex items-start justify-between">
        <div>
          <h3 className="text-lg font-bold text-slate-900">Evidence Trust Scorecard</h3>
          <p className="text-sm text-slate-500 mt-0.5">
            {report.document_name}
            <span className="mx-1.5 text-slate-300">·</span>
            <span className="capitalize">{report.document_type.replace(/_/g, " ")}</span>
          </p>
        </div>
        <div className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold border ${risk.bg} ${risk.text} ${risk.border}`}>
          <span className={`w-1.5 h-1.5 rounded-full ${risk.dot}`} />
          {risk.label}
        </div>
      </div>

      {/* Score + Stats */}
      <div className="flex items-center gap-8">
        <ScoreRing score={report.trust_score} />

        <div className="flex-1 grid grid-cols-3 gap-4">
          <StatCard
            value={report.verified_count}
            label="Verified"
            icon="✓"
            iconBg="bg-emerald-100 text-emerald-600"
          />
          <StatCard
            value={report.unverifiable_count}
            label="Unverifiable"
            icon="?"
            iconBg="bg-amber-100 text-amber-600"
          />
          <StatCard
            value={report.contradicted_count}
            label="Contradicted"
            icon="✗"
            iconBg="bg-red-100 text-red-600"
          />
        </div>
      </div>
    </div>
  );
}

function StatCard({ value, label, icon, iconBg }: {
  value: number; label: string; icon: string; iconBg: string;
}) {
  return (
    <div className="flex items-center gap-3 bg-slate-50/70 rounded-xl p-3">
      <div className={`w-9 h-9 rounded-lg flex items-center justify-center text-sm font-bold shrink-0 ${iconBg}`}>
        {icon}
      </div>
      <div>
        <div className="text-xl font-bold text-slate-900">{value}</div>
        <div className="text-[11px] text-slate-500 font-medium">{label}</div>
      </div>
    </div>
  );
}
