import { useState, useEffect } from "react";
import type { Challenge } from "../hooks/useVerification";

interface Props {
  onRun: (challenge: Challenge) => void;
}

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
    <div>
      <div className="text-center mb-8">
        <h2 className="text-2xl font-bold text-gray-900">⚔️ Challenge VerifyFlow</h2>
        <p className="text-gray-500 mt-2">
          Pre-loaded adversarial inputs — watch the deterministic verifier reject manipulations live
        </p>
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        {challenges.map((c) => (
          <button
            key={c.id}
            onClick={() => runChallenge(c.id)}
            className="text-left bg-white border border-gray-200 rounded-xl p-5 hover:border-red-300 hover:shadow-md transition-all"
          >
            <h3 className="font-semibold text-gray-900">{c.name}</h3>
            <p className="text-sm text-gray-500 mt-1">{c.description}</p>
            <span className="inline-block mt-3 text-xs font-medium text-red-600 bg-red-50 px-2 py-1 rounded">
              Run Challenge →
            </span>
          </button>
        ))}
      </div>
    </div>
  );
}
