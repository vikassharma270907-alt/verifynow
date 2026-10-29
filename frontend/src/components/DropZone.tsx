import { useState, useCallback, useRef, type DragEvent, type KeyboardEvent } from "react";
import { ALLOWED_EXTENSIONS, MAX_UPLOAD_BYTES, MAX_UPLOAD_MB } from "../config";

interface Props { onFileDrop: (file: File) => void }

const ALLOWED: readonly string[] = ALLOWED_EXTENSIONS;

function validate(file: File): string | null {
  const dot = file.name.lastIndexOf(".");
  const ext = dot >= 0 ? file.name.slice(dot).toLowerCase() : "";
  if (!ALLOWED.includes(ext)) {
    return `Unsupported file type. Use ${ALLOWED.map((e) => e.slice(1).toUpperCase()).join(", ")}.`;
  }
  if (file.size > MAX_UPLOAD_BYTES) {
    return `That file is larger than ${MAX_UPLOAD_MB} MB. Choose a smaller one.`;
  }
  return null;
}

export default function DropZone({ onFileDrop }: Props) {
  const [over, setOver] = useState(false);
  const [problem, setProblem] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const accept = useCallback((f: File | undefined) => {
    if (!f) return;
    const msg = validate(f);
    setProblem(msg);
    if (!msg) onFileDrop(f);
  }, [onFileDrop]);

  const handleDrop = useCallback((e: DragEvent<HTMLDivElement>) => {
    e.preventDefault(); setOver(false);
    accept(e.dataTransfer.files[0]);
  }, [accept]);

  const handlePick = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    accept(e.target.files?.[0]);
    e.target.value = ""; // allow re-selecting the same file
  }, [accept]);

  const openPicker = () => inputRef.current?.click();

  const handleKeyDown = (e: KeyboardEvent<HTMLDivElement>) => {
    if (e.target !== e.currentTarget) return;
    if (e.key === "Enter" || e.key === " ") {
      e.preventDefault();
      openPicker();
    }
  };

  return (
    <div className="space-y-6 sm:space-y-10">
      {/* Hero */}
      <div className="text-center space-y-2 sm:space-y-3">
        <h2 className="text-[22px] sm:text-[28px] font-bold tracking-tight" style={{ color: "var(--text-primary)" }}>
          Verify any document
        </h2>
        <p className="text-[14px] sm:text-[15px] max-w-md mx-auto" style={{ color: "var(--text-secondary)", lineHeight: 1.6 }}>
          Drop a contract, invoice, or legal notice. Every claim gets extracted,
          checked against live evidence, and scored.
        </p>
      </div>

      {/* Drop area */}
      <div
        role="button"
        tabIndex={0}
        aria-label={`Drop a file here, or press Enter to browse. PDF, TXT or MD, up to ${MAX_UPLOAD_MB} MB`}
        onClick={openPicker}
        onKeyDown={handleKeyDown}
        onDragOver={(e) => { e.preventDefault(); setOver(true); }}
        onDragLeave={() => setOver(false)}
        onDrop={handleDrop}
        className="relative rounded-xl border-2 border-dashed px-4 py-10 sm:px-6 sm:py-16 text-center transition-all duration-200 cursor-pointer focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2"
        style={{
          borderColor: over ? "var(--brand)" : "var(--border)",
          background: over ? "var(--brand-soft)" : "var(--card)",
          transform: over ? "scale(1.005)" : "scale(1)",
        }}
      >
        <div className="space-y-4">
          <div
            className="mx-auto w-12 h-12 rounded-xl flex items-center justify-center"
            style={{ background: "var(--brand-soft)" }}
          >
            <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="var(--brand)" strokeWidth="1.5">
              <path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8Z" />
              <polyline points="14 2 14 8 20 8" />
              <line x1="12" y1="18" x2="12" y2="12" />
              <line x1="9" y1="15" x2="15" y2="15" />
            </svg>
          </div>
          <div>
            <p className="text-[15px] font-medium" style={{ color: "var(--text-primary)" }}>
              {over ? "Release to verify" : "Drop your file here"}
            </p>
            <p className="text-sm mt-1" style={{ color: "var(--text-tertiary)" }}>
              or choose from your computer
            </p>
          </div>
          <span
            aria-hidden="true"
            className="inline-block px-4 py-2 rounded-md text-sm font-medium text-white transition-opacity hover:opacity-90"
            style={{ background: "var(--brand)" }}
          >
            Browse files
          </span>
          <input
            ref={inputRef}
            type="file"
            accept={ALLOWED.join(",")}
            onChange={handlePick}
            onClick={(e) => e.stopPropagation()}
            tabIndex={-1}
            className="hidden"
          />
          <p className="text-xs" style={{ color: "var(--text-tertiary)" }}>
            PDF, TXT, MD — max {MAX_UPLOAD_MB} MB
          </p>
          {problem && (
            <p
              role="alert"
              className="text-[13px] px-3 py-2 rounded-md inline-block"
              style={{ background: "var(--contradicted-soft)", color: "var(--contradicted)" }}
            >
              {problem}
            </p>
          )}
        </div>
      </div>

      {/* Pipeline strip */}
      <div className="flex items-center justify-center flex-wrap gap-1 sm:gap-1.5 text-[10px] sm:text-[11px]" style={{ color: "var(--text-tertiary)" }}>
        {[
          { label: "Extract", color: "var(--brand)" },
          { label: "Search", color: "var(--unverifiable)" },
          { label: "Analyze", color: "#8B5CF6" },
          { label: "Verify", color: "var(--verified)" },
          { label: "Summarize", color: "var(--contradicted)" },
        ].map((s, i) => (
          <span key={i} className="flex items-center gap-1 sm:gap-1.5">
            {i > 0 && <span className="hidden sm:inline" style={{ color: "var(--border)" }}>→</span>}
            <span className="w-1.5 h-1.5 rounded-full" style={{ background: s.color }} />
            <span>{s.label}</span>
          </span>
        ))}
      </div>
    </div>
  );
}
