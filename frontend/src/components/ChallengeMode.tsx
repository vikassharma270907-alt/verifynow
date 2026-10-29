import { useState, useEffect } from "react";
import type { Challenge } from "../hooks/useVerification";

interface Props { onRun: (c: Challenge) => void }

const icons: Record<string, string> = {
  "homograph-attack": "🔗", "prompt-injection": "💉",
  "fabricated-entity": "🏛️", "contradictory-terms": "⚖️",
  "invoice-fraud": "🧾",
};

export default function ChallengeMode({ onRun }: Props) {
  const [list, setList] = useState<Challenge[]>([]);

  useEffect(() => {
    fetch("/api/challenges").then(r => r.json()).then(setList).catch(() => setList([]));
  }, []);

  const run = async (id: string) => {
    const r = await fetch(`/api/challenges/${encodeURIComponent(id)}`);
    onRun(await r.json());
  };

  return (
    <div className="space-y-8">
      <div className="text-center space-y-2">
        <h2 className="text-[20px] sm:text-[22px] font-bold" style={{ fontFamily: "'DM Sans'" }}>Challenge the verifier</h2>
        <p className="text-[15px]" style={{ color: "var(--text-secondary)" }}>
          Adversarial documents that test the deterministic trust gate.
        </p>
      </div>
      <div className="grid gap-2 sm:grid-cols-2">
        {list.map(c => (
          <button key={c.id} onClick={() => run(c.id)}
            className="group text-left rounded-lg border p-4 transition-all hover:shadow-sm"
            style={{ background: "var(--card)", borderColor: "var(--border)" }}>
            <div className="flex gap-3">
              <span className="text-xl shrink-0">{icons[c.id] ?? "🧪"}</span>
              <div>
                <p className="text-sm font-semibold" style={{ color: "var(--text-primary)" }}>{c.name}</p>
                <p className="text-xs mt-1" style={{ color: "var(--text-tertiary)", lineHeight: 1.5 }}>{c.description}</p>
              </div>
            </div>
          </button>
        ))}
      </div>
    </div>
  );
}
