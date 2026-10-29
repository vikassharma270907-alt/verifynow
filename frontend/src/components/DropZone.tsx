import { useState, useCallback, type DragEvent } from "react";

interface Props {
  onFileDrop: (file: File) => void;
}

const ALLOWED = new Set([".pdf", ".txt", ".png", ".jpg", ".jpeg", ".webp"]);

export default function DropZone({ onFileDrop }: Props) {
  const [dragging, setDragging] = useState(false);

  const handleDrop = useCallback(
    (e: DragEvent<HTMLDivElement>) => {
      e.preventDefault();
      setDragging(false);
      const file = e.dataTransfer.files[0];
      if (file) onFileDrop(file);
    },
    [onFileDrop]
  );

  const handleFileSelect = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const file = e.target.files?.[0];
      if (file) onFileDrop(file);
    },
    [onFileDrop]
  );

  return (
    <div
      onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
      onDragLeave={() => setDragging(false)}
      onDrop={handleDrop}
      className={`
        border-2 border-dashed rounded-2xl p-16 text-center transition-all cursor-pointer
        ${dragging ? "border-blue-500 bg-blue-50" : "border-gray-300 bg-white hover:border-gray-400"}
      `}
    >
      <div className="text-5xl mb-4">📄</div>
      <h2 className="text-xl font-semibold text-gray-800 mb-2">
        Drop a document to verify
      </h2>
      <p className="text-gray-500 mb-6">
        PDF, text, or image — we'll extract every claim and check it against live evidence
      </p>
      <label className="inline-block px-6 py-3 bg-blue-600 text-white font-medium rounded-lg hover:bg-blue-700 transition-colors cursor-pointer">
        Choose File
        <input
          type="file"
          accept={[...ALLOWED].join(",")}
          onChange={handleFileSelect}
          className="hidden"
        />
      </label>
      <p className="mt-4 text-xs text-gray-400">
        Supports: {[...ALLOWED].join(", ")} · Max 20MB
      </p>
    </div>
  );
}
