import type { VerificationReport } from "../hooks/useVerification";

interface Props { report: VerificationReport }

const riskStyle: Record<string, { bg: string; fg: string; dot: string; label: string }> = {
  low:      { bg: "var(--verified-soft)",      fg: "var(--verified)",      dot: "var(--verified)",      label: "Low risk" },
  medium:   { bg: "var(--unverifiable-soft)",   fg: "var(--unverifiable)",  dot: "var(--unverifiable)",  label: "Medium risk" },
  high:     { bg: "#FFF7ED",                    fg: "#EA580C",             dot: "#EA580C",              label: "High risk" },
  critical: { bg: "var(--contradicted-soft)",   fg: "var(--contradicted)",  dot: "var(--contradicted)",  label: "Critical risk" },
};

function ringColor(s: number) {
  if (s >= 75) return "var(--verified)";
  if (s >= 50) return "var(--unverifiable)";
  if (s >= 30) return "#EA580C";
  return "var(--contradicted)";
}

function Ring({ score }: { score: number }) {
  const r = 42, c = 2 * Math.PI * r;
  const offset = c - (score / 100) * c;
  const color = ringColor(score);
  return (
    <div className="relative w-[100px] h-[100px] shrink-0">
      <svg viewBox="0 0 100 100" className="w-full h-full" style={{ transform: "rotate(-90deg)" }}>
        <circle cx="50" cy="50" r={r} fill="none" stroke="var(--border)" strokeWidth="7" />
        <circle cx="50" cy="50" r={r} fill="none" stroke={color} strokeWidth="7"
          strokeLinecap="round" strokeDasharray={c} strokeDashoffset={offset} className="score-ring" />
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <span className="text-2xl font-bold" style={{ color, fontFamily: "'DM Sans'" }}>{score.toFixed(0)}</span>
        <span className="text-[10px] font-medium" style={{ color: "var(--text-tertiary)" }}>trust %</span>
      </div>
    </div>
  );
}

export default function TrustScorecard({ report }: Props) {
  const risk = riskStyle[report.risk_level] ?? riskStyle.medium;
  return (
    <div className="rounded-xl border p-6 space-y-6" style={{ background: "var(--card)", borderColor: "var(--border)" }}>
      <div className="flex items-start justify-between">
        <div>
          <h3 className="text-base font-bold" style={{ fontFamily: "'DM Sans'" }}>Evidence Trust Scorecard</h3>
          <p className="text-sm mt-0.5" style={{ color: "var(--text-tertiary)" }}>
            {report.document_name} · {report.document_type.replace(/_/g, " ")}
          </p>
        </div>
        <span className="inline-flex items-center gap-1.5 text-xs font-semibold px-2.5 py-1 rounded-md" style={{ background: risk.bg, color: risk.fg }}>
          <span className="w-1.5 h-1.5 rounded-full" style={{ background: risk.dot }} />
          {risk.label}
        </span>
      </div>
      <div className="flex items-center gap-8">
        <Ring score={report.trust_score} />
        <div className="flex-1 grid grid-cols-3 gap-3">
          <Stat value={report.verified_count} label="Verified" color="var(--verified)" />
          <Stat value={report.unverifiable_count} label="Unverifiable" color="var(--unverifiable)" />
          <Stat value={report.contradicted_count} label="Contradicted" color="var(--contradicted)" />
        </div>
      </div>
    </div>
  );
}

function Stat({ value, label, color }: { value: number; label: string; color: string }) {
  return (
    <div className="rounded-lg p-3" style={{ background: "var(--surface)" }}>
      <div className="text-xl font-bold" style={{ color, fontFamily: "'DM Sans'" }}>{value}</div>
      <div className="text-[11px] font-medium mt-0.5" style={{ color: "var(--text-tertiary)" }}>{label}</div>
    </div>
  );
}
