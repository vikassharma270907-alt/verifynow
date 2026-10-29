import { useState, useEffect } from "react";

const STEPS = [
  { id: "extract",  icon: "⚡", label: "Extracting claims",       detail: "Nemotron-3-Nano · $0.06/1M",   color: "text-blue-600",    bg: "bg-blue-50" },
  { id: "search",   icon: "🔍", label: "Searching evidence",      detail: "Tavily Live Search",            color: "text-amber-600",   bg: "bg-amber-50" },
  { id: "analyze",  icon: "🧠", label: "Deep analysis",            detail: "Nemotron-3-Super · $0.30/1M",  color: "text-violet-600",  bg: "bg-violet-50" },
  { id: "verify",   icon: "🔒", label: "Deterministic verification", detail: "Code verifier · no LLM",     color: "text-emerald-600", bg: "bg-emerald-50" },
  { id: "summarize",icon: "📋", label: "Generating summary",       detail: "Nemotron-3-Ultra · $1.00/1M",  color: "text-rose-600",    bg: "bg-rose-50" },
];

export default function LoadingPipeline() {
  const [activeStep, setActiveStep] = useState(0);

  useEffect(() => {
    const timer = setInterval(() => {
      setActiveStep((prev) => (prev < STEPS.length - 1 ? prev + 1 : prev));
    }, 5000);
    return () => clearInterval(timer);
  }, []);

  return (
    <div className="max-w-md mx-auto py-16 space-y-8">
      <div className="text-center space-y-2">
        <div className="inline-block w-10 h-10 border-[3px] border-slate-200 border-t-[var(--color-brand)] rounded-full animate-spin" />
        <h3 className="text-lg font-semibold text-slate-800">Verifying document</h3>
        <p className="text-sm text-slate-400">Running the full pipeline</p>
      </div>

      <div className="space-y-2">
        {STEPS.map((step, i) => {
          const isDone = i < activeStep;
          const isActive = i === activeStep;
          const isPending = i > activeStep;

          return (
            <div
              key={step.id}
              className={`pipeline-step flex items-center gap-3 rounded-xl px-4 py-3 transition-all duration-300 ${
                isActive ? `${step.bg} border border-slate-200/50` : "bg-transparent"
              }`}
            >
              {/* Icon */}
              <div className={`w-8 h-8 rounded-lg flex items-center justify-center text-sm shrink-0 ${
                isDone ? "bg-emerald-100" :
                isActive ? `${step.bg}` :
                "bg-slate-100"
              }`}>
                {isDone ? (
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#059669" strokeWidth="3">
                    <polyline points="20 6 9 17 4 12" />
                  </svg>
                ) : (
                  <span className={isPending ? "opacity-40" : ""}>{step.icon}</span>
                )}
              </div>

              {/* Text */}
              <div className="flex-1 min-w-0">
                <p className={`text-sm font-medium ${
                  isDone ? "text-emerald-700" :
                  isActive ? step.color :
                  "text-slate-400"
                }`}>
                  {step.label}
                </p>
                <p className={`text-[11px] ${
                  isDone ? "text-emerald-500" :
                  isActive ? "text-slate-500" :
                  "text-slate-300"
                }`}>
                  {step.detail}
                </p>
              </div>

              {/* Active indicator */}
              {isActive && (
                <div className="w-2 h-2 rounded-full bg-[var(--color-brand)] pulse-dot shrink-0" />
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
