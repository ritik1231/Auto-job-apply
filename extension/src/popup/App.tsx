import { useState } from "react";
import { useAuth } from "@/popup/hooks/use-auth";
import ResumePanel from "@/popup/components/ResumePanel";
import AnalyseFlow from "@/popup/components/AnalyseFlow";
import HistoryPanel from "@/popup/components/HistoryPanel";
import { useHistoryStore } from "@/popup/stores/history-store";

type Tab = "analyse" | "history";

export default function App() {
  const {
    isAuthenticated,
    isLoading: authLoading,
    user,
    signIn,
    signOut,
    error: authError,
  } = useAuth();
  const [tab, setTab] = useState<Tab>("analyse");
  const loadHistory = useHistoryStore((s) => s.load);

  function switchTab(next: Tab) {
    setTab(next);
    if (next === "history") void loadHistory();
  }

  if (authLoading) {
    return (
      <div className="w-[360px] min-h-[200px] bg-white p-5 font-sans flex items-center justify-center">
        <p className="text-sm text-gray-400">Loading…</p>
      </div>
    );
  }

  if (!isAuthenticated) {
    return (
      <div className="w-[360px] min-h-[240px] bg-white p-5 font-sans">
        <h1 className="text-xl font-semibold text-gray-900">AI Job Apply</h1>
        <p className="mt-2 text-sm text-gray-500">
          Sign in with Google to apply to LinkedIn hiring posts in seconds.
        </p>
        <button
          onClick={() => void signIn()}
          className="mt-6 w-full rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700"
        >
          Sign in with Google
        </button>
        {authError && <p className="mt-3 text-sm text-red-600">{authError}</p>}
      </div>
    );
  }

  return (
    <div className="w-[360px] bg-white p-5 font-sans">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold text-gray-900">AI Job Apply</h1>
        <button
          onClick={() => void signOut()}
          className="text-xs text-gray-400 hover:text-gray-600"
        >
          Sign out
        </button>
      </div>
      {user && (
        <p className="mt-0.5 text-xs text-gray-500">
          {user.name ?? user.email}
        </p>
      )}

      <ResumePanel />

      {/* Tab bar */}
      <div className="mt-5 flex border-b border-gray-200">
        {(["analyse", "history"] as Tab[]).map((t) => (
          <button
            key={t}
            onClick={() => switchTab(t)}
            className={`pb-2 px-3 text-sm font-medium capitalize transition-colors ${
              tab === t
                ? "border-b-2 border-blue-600 text-blue-600"
                : "text-gray-400 hover:text-gray-600"
            }`}
          >
            {t}
          </button>
        ))}
      </div>

      {/* Tab content */}
      <div className="mt-4">
        {tab === "analyse" ? <AnalyseFlow /> : <HistoryPanel />}
      </div>
    </div>
  );
}
