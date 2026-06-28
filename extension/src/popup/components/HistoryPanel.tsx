import { useEffect } from "react";
import { useHistoryStore } from "@/popup/stores/history-store";
import type { ApplicationHistoryItem } from "@/shared/types";

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
  });
}

function StatusBadge({ status }: { status: ApplicationHistoryItem["status"] }) {
  const styles: Record<ApplicationHistoryItem["status"], string> = {
    sent: "bg-green-50 text-green-700 border-green-200",
    draft: "bg-gray-50 text-gray-500 border-gray-200",
    failed: "bg-red-50 text-red-600 border-red-200",
  };
  return (
    <span
      className={`rounded-full border px-2 py-0.5 text-xs font-medium ${styles[status]}`}
    >
      {status}
    </span>
  );
}

function HistoryRow({ item }: { item: ApplicationHistoryItem }) {
  const label =
    [item.job_title, item.company].filter(Boolean).join(" · ") ||
    "Unknown role";
  const date = item.sent_at ?? item.created_at;
  const pct =
    item.match_score !== null ? Math.round(item.match_score * 100) : null;

  return (
    <li className="flex items-start justify-between gap-2 py-2.5 border-b border-gray-100 last:border-0">
      <div className="min-w-0">
        <p className="text-xs font-medium text-gray-900 truncate max-w-[200px]">
          {label}
        </p>
        <p className="text-xs text-gray-400 mt-0.5">{formatDate(date)}</p>
      </div>
      <div className="flex flex-col items-end gap-1 shrink-0">
        <StatusBadge status={item.status} />
        {pct !== null && (
          <span className="text-xs text-gray-400">{pct}% match</span>
        )}
      </div>
    </li>
  );
}

export default function HistoryPanel() {
  const { items, isLoading, error, load } = useHistoryStore();

  useEffect(() => {
    void load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  if (isLoading) {
    return <p className="py-6 text-center text-xs text-gray-400">Loading…</p>;
  }

  if (error) {
    return (
      <div className="py-4 text-center">
        <p className="text-xs text-red-600">{error}</p>
        <button
          onClick={() => void load()}
          className="mt-2 text-xs text-blue-600 hover:text-blue-800"
        >
          Retry
        </button>
      </div>
    );
  }

  if (items.length === 0) {
    return (
      <p className="py-8 text-center text-xs text-gray-400">
        No applications yet. Analyse a LinkedIn post to get started.
      </p>
    );
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-1">
        <p className="text-xs text-gray-400">
          {items.length} application{items.length !== 1 ? "s" : ""}
        </p>
        <button
          onClick={() => void load()}
          className="text-xs text-gray-400 hover:text-gray-600"
        >
          Refresh
        </button>
      </div>
      <ul>
        {items.map((item) => (
          <HistoryRow key={item.id} item={item} />
        ))}
      </ul>
    </div>
  );
}
