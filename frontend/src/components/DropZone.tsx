import { useState, useCallback, type DragEvent } from "react";

interface Props {
  onFileDrop: (file: File) => void;
}

const ALLOWED = new Set([".pdf", ".txt", ".png", ".jpg", ".jpeg", ".webp"]);

export default function DropZone({ onFileDrop }: Props) {
  const [dragging, setDragging] = useState(false);
  const handleDrop = useCallback((e: DragEvent<HTMLDivElement>) => {
    e.preventDefault(); setDragging(false);
    const file = e.dataTransfer.files[0];
    if (file) onFileDrop(file);
  }, [onFileDrop]);
  const handleFileSelect = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) onFileDrop(file);
  }, [onFileDrop]);

  return (
    <div className="space-y-8">
      <div className="text-center space-y-3 pt-4">
        <h2 className="text-3xl font-bold tracking-tight text-slate-900">Verify any document in seconds</h2>
        <p className="text-base text-slate-500 max-w-lg mx-auto leading-relaxed">
          Drop a contract, legal notice, or invoice. We extract every claim, check it against live web evidence, and give you an auditable trust report.
        </p>
      </div>
      <div onDragOver={(e) => { e.preventDefault(); setDragging(true); }} onDragLeave={() => setDragging(false)} onDrop={handleDrop}
        className={`group relative overflow-hidden border-2 border-dashed rounded-2xl px-8 py-20 text-center transition-all duration-300 cursor-pointer ${dragging ? "border-[var(--color-brand)] bg-[var(--color-brand-light)] scale-[1.01]" : "border-slate-200 bg-white hover:border-slate-300 hover:shadow-lg hover:shadow-slate-100"}`}>
        <div className="absolute top-4 left-4 w-6 h-6 border-t-2 border-l-2 border-slate-200 rounded-tl-lg opacity-40" />
        <div className="absolute top-4 right-4 w-6 h-6 border-t-2 border-r-2 border-slate-200 rounded-tr-lg opacity-40" />
        <div className="absolute bottom-4 left-4 w-6 h-6 border-b-2 border-l-2 border-slate-200 rounded-bl-lg opacity-40" />
        <div className="absolute bottom-4 right-4 w-6 h-6 border-b-2 border-r-2 border-slate-200 rounded-br-lg opacity-40" />
        <div className="relative z-10 space-y-5">
          <div className="mx-auto w-16 h-16 rounded-2xl bg-slate-50 border border-slate-100 flex items-center justify-center group-hover:bg-[var(--color-brand-light)] transition-colors">
            <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" className="text-slate-400 group-hover:text-[var(--color-brand)] transition-colors">
              <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8Z" />
              <polyline points="14 2 14 8 20 8" /><line x1="12" y1="18" x2="12" y2="12" /><line x1="9" y1="15" x2="15" y2="15" />
            </svg>
          </div>
          <div className="space-y-1">
            <p className="text-base font-semibold text-slate-700">{dragging ? "Release to verify" : "Drop your document here"}</p>
            <p className="text-sm text-slate-400">or click to browse files</p>
          </div>
          <label className="inline-flex items-center gap-2 px-5 py-2.5 bg-[var(--color-brand)] text-white text-sm font-medium rounded-lg hover:bg-blue-700 active:scale-[0.98] transition-all cursor-pointer shadow-sm shadow-blue-200">
            Choose File
            <input type="file" accept={[...ALLOWED].join(",")} onChange={handleFileSelect} className="hidden" />
          </label>
          <p className="text-xs text-slate-400">PDF · TXT · PNG · JPG · WEBP — up to 20 MB</p>
        </div>
      </div>
      <div className="flex items-center justify-center gap-2 text-xs text-slate-400 flex-wrap">
        <span className="text-blue-500">⚡ <span className="text-slate-500">Nano extracts</span></span>
        <span className="text-slate-300">→</span>
        <span className="text-amber-500">🔍 <span className="text-slate-500">Tavily searches</span></span>
        <span className="text-slate-300">→</span>
        <span className="text-violet-500">🧠 <span className="text-slate-500">Super analyzes</span></span>
        <span className="text-slate-300">→</span>
        <span className="text-emerald-500">🔒 <span className="text-slate-500">Code verifies</span></span>
        <span className="text-slate-300">→</span>
        <span className="text-rose-500">📋 <span className="text-slate-500">Ultra summarizes</span></span>
      </div>
    </div>
  );
}
