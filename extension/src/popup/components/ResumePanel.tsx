import { useEffect, useRef } from "react";
import { useResumeStore } from "@/popup/stores/resume-store";

function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${Math.round(bytes / 1024)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}

export default function ResumePanel() {
  const {
    resumes,
    activeId,
    isLoading,
    isUploading,
    error,
    loadResumes,
    uploadResume,
    deleteResume,
  } = useResumeStore();
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    void loadResumes();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  function handleFileChange(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (file) void uploadResume(file);
    e.target.value = "";
  }

  const activeResume = resumes.find((r) => r.id === activeId) ?? null;

  return (
    <div className="mt-4">
      <div className="flex items-center justify-between mb-1.5">
        <h2 className="text-xs font-semibold uppercase tracking-wide text-gray-500">
          Resume
        </h2>
        {activeResume && (
          <button
            onClick={() => inputRef.current?.click()}
            disabled={isUploading}
            className="text-xs text-blue-600 hover:text-blue-800 disabled:opacity-50"
          >
            {isUploading ? "Uploading…" : "Replace"}
          </button>
        )}
      </div>

      <input
        ref={inputRef}
        type="file"
        accept=".pdf,application/pdf"
        className="hidden"
        onChange={handleFileChange}
      />

      {isLoading ? (
        <p className="text-xs text-gray-400 py-3 text-center">Loading…</p>
      ) : activeResume ? (
        <div className="flex items-center justify-between rounded-lg border border-gray-200 bg-gray-50 px-3 py-2.5">
          <div className="min-w-0">
            <p className="text-xs font-medium text-gray-900 truncate max-w-[220px]">
              {activeResume.file_name}
            </p>
            <p className="text-xs text-gray-500 mt-0.5">
              {formatBytes(activeResume.file_size)} ·{" "}
              {formatDate(activeResume.created_at)}
            </p>
          </div>
          <button
            onClick={() => void deleteResume(activeResume.id)}
            className="ml-3 shrink-0 text-xs text-gray-400 hover:text-red-500 transition-colors"
          >
            Remove
          </button>
        </div>
      ) : (
        <button
          onClick={() => inputRef.current?.click()}
          disabled={isUploading}
          className="w-full rounded-lg border border-dashed border-gray-300 py-4 text-center text-xs text-gray-400 hover:border-blue-400 hover:text-blue-500 transition-colors disabled:opacity-50"
        >
          {isUploading ? "Uploading…" : "Click to upload a PDF resume"}
        </button>
      )}

      {error && <p className="mt-1.5 text-xs text-red-600">{error}</p>}
    </div>
  );
}
