import { useState, useEffect } from "react";
import type { Challenge } from "../hooks/useVerification";

interface Props {
  onRun: (challenge: Challenge) => void;
}

const challengeIcons: Record<string, string> = {
  "homograph-attack": "🔗",
  "prompt-injection": "💉",
  "fabricated-entity": "🏛️",
  "contradictory-terms": "⚖️",
};

export default function ChallengeMode({ onRun }: Props) {
  const [challenges, setChallenges] = useState<Challenge[]>([]);

  useEffect(() => {
    fetch("/api/challenges")
      .then((r) => r.json())
      .then(setChallenges)
      .catch(() => setChallenges([]));
  }, []);

  const runChallenge = async (id: string) => {
    const resp = await fetch(`/api/challenges/${encodeURIComponent(id)}`);
    const full: Challenge = await resp.json();
    onRun(full);
  };

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="text-center space-y-3 pt-4">
        <div className="inline-flex items-center justify-center w-14 h-14 rounded-2xl bg-red-50 border border-red-100 mb-1">
          <span className="text-2xl">⚔️</span>
        </div>
        <h2 className="text-2xl font-bold tracking-tight text-slate-900">
          Challenge VerifyFlow
        </h2>
        <p className="text-sm text-slate-500 max-w-md mx-auto leading-relaxed">
          Pre-loaded adversarial documents. Watch the deterministic verifier
          catch manipulation attempts in real time.
        </p>
      </div>

      {/* Challenge grid */}
      <div className="grid gap-3 sm:grid-cols-2">
        {challenges.map((c) => (
          <button
            key={c.id}
            onClick={() => runChallenge(c.id)}
            className="group text-left glass-card rounded-xl p-5 hover:shadow-lg hover:shadow-red-50 hover:border-red-200 transition-all duration-200"
          >
            <div className="flex items-start gap-3">
              <span className="text-2xl shrink-0 mt-0.5">
                {challengeIcons[c.id] ?? "🧪"}
              </span>
              <div className="space-y-1.5 min-w-0">
                <h3 className="text-sm font-semibold text-slate-800 group-hover:text-red-700 transition-colors">
                  {c.name}
                </h3>
                <p className="text-xs text-slate-500 leading-relaxed">
                  {c.description}
                </p>
                <span className="inline-flex items-center gap-1 text-[11px] font-medium text-red-500 opacity-0 group-hover:opacity-100 transition-opacity">
                  Run challenge
                  <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <line x1="5" y1="12" x2="19" y2="12" />
                    <polyline points="12 5 19 12 12 19" />
                  </svg>
                </span>
              </div>
            </div>
          </button>
        ))}
      </div>
    </div>
  );
}
