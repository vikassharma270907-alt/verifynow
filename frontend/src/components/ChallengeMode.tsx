import { useState, useEffect, useRef } from "react";
import type { Challenge } from "../hooks/useVerification";
import { isAbortError } from "../config";

interface Props { onRun: (c: Challenge) => void }

const icons: Record<string, string> = {
  "homograph-attack": "🔗", "prompt-injection": "💉",
  "fabricated-entity": "🏛️", "contradictory-terms": "⚖️",
  "invoice-fraud": "🧾",
};

async function readJson<T>(resp: Response): Promise<T> {
  if (!resp.ok) {
    const body = await resp.json().catch(() => ({ detail: resp.statusText }));
    throw new Error(body?.detail || `HTTP ${resp.status}`);
  }
  return resp.json();
}

export default function ChallengeMode({ onRun }: Props) {
  const [list, setList] = useState<Challenge[]>([]);
  const [error, setError] = useState<string | null>(null);
  const runRef = useRef<AbortController | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    fetch("/api/challenges", { signal: controller.signal })
      .then((r) => readJson<Challenge[]>(r))
      .then((data) => {
        if (controller.signal.aborted) return;
        setList(Array.isArray(data) ? data : []);
        setError(null);
      })
      .catch((err) => {
        if (controller.signal.aborted || isAbortError(err)) return;
        setList([]);
        setError(`Could not load challenges. ${err instanceof Error ? err.message : ""}`.trim());
      });
    return () => controller.abort();
  }, []);

  // Abort an in-flight challenge fetch when leaving the tab.
  useEffect(() => () => runRef.current?.abort(), []);

  const run = async (id: string) => {
    runRef.current?.abort();
    const controller = new AbortController();
    runRef.current = controller;
    setError(null);
    try {
      const r = await fetch(`/api/challenges/${encodeURIComponent(id)}`, { signal: controller.signal });
      const challenge = await readJson<Challenge>(r);
      if (controller.signal.aborted) return;
      onRun(challenge);
    } catch (err) {
      if (controller.signal.aborted || isAbortError(err)) return;
      setError(`Could not run that challenge. ${err instanceof Error ? err.message : ""}`.trim());
    }
  };

  return (
    <div className="space-y-8">
      <div className="text-center space-y-2">
        <h2 className="text-[20px] sm:text-[22px] font-bold" style={{ fontFamily: "'DM Sans'" }}>Challenge the verifier</h2>
        <p className="text-[15px]" style={{ color: "var(--text-secondary)" }}>
          Adversarial documents that test the deterministic trust gate.
        </p>
      </div>
      {error && (
        <p role="alert" className="text-[13px] px-3 py-2 rounded-md"
          style={{ background: "var(--contradicted-soft)", color: "var(--contradicted)" }}>{error}</p>
      )}
      <div className="grid gap-2 sm:grid-cols-2">
        {list.map(c => (
          <button key={c.id} onClick={() => run(c.id)}
            className="group text-left rounded-lg border p-4 transition-all hover:shadow-sm"
            style={{ background: "var(--card)", borderColor: "var(--border)" }}>
            <div className="flex gap-3">
              <span className="text-xl shrink-0" aria-hidden="true">{icons[c.id] ?? "🧪"}</span>
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
