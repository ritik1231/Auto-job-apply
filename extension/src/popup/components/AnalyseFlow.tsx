import { useEffect, useState } from "react";
import { useApplicationStore } from "@/popup/stores/application-store";
import { useQuotaStore } from "@/popup/stores/quota-store";
import type { ApplicationDraft, JobPost } from "@/shared/types";

// ── Helpers ───────────────────────────────────────────────────────────────────

function MatchBar({ score }: { score: number }) {
  const pct = Math.round(score * 100);
  const color =
    pct >= 70 ? "bg-green-500" : pct >= 45 ? "bg-yellow-400" : "bg-red-400";
  return (
    <div className="flex items-center gap-2">
      <div className="flex-1 h-1.5 rounded-full bg-gray-200">
        <div
          className={`h-1.5 rounded-full ${color}`}
          style={{ width: `${pct}%` }}
        />
      </div>
      <span className="text-xs font-semibold text-gray-700 w-8 text-right">
        {pct}%
      </span>
    </div>
  );
}

function Spinner() {
  return (
    <svg
      className="animate-spin h-5 w-5 text-blue-500"
      fill="none"
      viewBox="0 0 24 24"
    >
      <circle
        className="opacity-25"
        cx="12"
        cy="12"
        r="10"
        stroke="currentColor"
        strokeWidth="4"
      />
      <path
        className="opacity-75"
        fill="currentColor"
        d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"
      />
    </svg>
  );
}

// ── Quota bar ─────────────────────────────────────────────────────────────────

function QuotaBar() {
  const { quota, isLoading } = useQuotaStore();

  if (isLoading || !quota) return null;

  const pct = Math.round((quota.used / quota.cap) * 100);
  const h = Math.floor(quota.resets_in_seconds / 3600);
  const m = Math.floor((quota.resets_in_seconds % 3600) / 60);
  const resetLabel = h > 0 ? `${h}h ${m}m` : `${m}m`;

  if (quota.remaining === 0) {
    return (
      <div className="rounded-lg border border-orange-200 bg-orange-50 px-3 py-2.5 mb-3">
        <p className="text-xs font-semibold text-orange-700">
          Daily limit reached ({quota.cap} analyses used)
        </p>
        <p className="text-xs text-orange-600 mt-0.5">
          Resets in {resetLabel} · {quota.active_users} active user
          {quota.active_users !== 1 ? "s" : ""} sharing the pool
        </p>
      </div>
    );
  }

  return (
    <div className="mb-3">
      <div className="flex justify-between items-center mb-1">
        <span className="text-[10px] text-gray-400 uppercase tracking-wide">
          Daily analyses
        </span>
        <span className="text-[10px] text-gray-500">
          {quota.used}/{quota.cap} used · resets in {resetLabel}
        </span>
      </div>
      <div className="h-1 rounded-full bg-gray-100">
        <div
          className={`h-1 rounded-full transition-all ${
            pct >= 80 ? "bg-orange-400" : "bg-blue-400"
          }`}
          style={{ width: `${pct}%` }}
        />
      </div>
    </div>
  );
}

// ── Preview screen ────────────────────────────────────────────────────────────

function PreviewScreen({
  job,
  draft,
}: {
  job: JobPost;
  draft: ApplicationDraft;
}) {
  const { sendApplication, reset } = useApplicationStore();
  const { load: reloadQuota } = useQuotaStore();
  const [form, setForm] = useState({
    to: job.recruiter_email ?? "",
    subject: draft.generated_subject,
    body: draft.generated_email,
    sending: false,
  });

  async function handleSend() {
    setForm((s) => ({ ...s, sending: true }));
    await sendApplication(
      form.to || undefined,
      form.subject !== draft.generated_subject ? form.subject : undefined,
      form.body !== draft.generated_email ? form.body : undefined,
    );
    setForm((s) => ({ ...s, sending: false }));
    void reloadQuota();
  }

  return (
    <div className="flex flex-col gap-3">
      <div>
        <p className="text-sm font-semibold text-gray-900 leading-tight">
          {job.job_title ?? "Position"}
          {job.company ? ` at ${job.company}` : ""}
        </p>
        {job.recruiter_name && (
          <p className="text-xs text-gray-500 mt-0.5">{job.recruiter_name}</p>
        )}
      </div>

      <div>
        <div className="flex items-center justify-between mb-1">
          <span className="text-xs font-medium text-gray-500">
            Resume match
          </span>
        </div>
        <MatchBar score={draft.match_score} />
        <div className="mt-1.5 flex flex-wrap gap-1">
          {draft.matching_skills.slice(0, 5).map((s) => (
            <span
              key={s}
              className="rounded-full bg-green-50 border border-green-200 px-2 py-0.5 text-xs text-green-700"
            >
              {s}
            </span>
          ))}
          {draft.missing_skills.slice(0, 3).map((s) => (
            <span
              key={s}
              className="rounded-full bg-gray-50 border border-gray-200 px-2 py-0.5 text-xs text-gray-500 line-through"
            >
              {s}
            </span>
          ))}
        </div>
      </div>

      <div className="flex flex-col gap-2">
        <div>
          <label className="text-xs font-medium text-gray-500 block mb-1">
            Subject
          </label>
          <input
            type="text"
            value={form.subject}
            onChange={(e) =>
              setForm((s) => ({ ...s, subject: e.target.value }))
            }
            className="w-full rounded-md border border-gray-300 px-3 py-1.5 text-xs text-gray-900 focus:border-blue-400 focus:outline-none"
          />
        </div>
        <div>
          <label className="text-xs font-medium text-gray-500 block mb-1">
            Email body
          </label>
          <textarea
            value={form.body}
            onChange={(e) => setForm((s) => ({ ...s, body: e.target.value }))}
            rows={8}
            className="w-full rounded-md border border-gray-300 px-3 py-2 text-xs text-gray-900 leading-relaxed focus:border-blue-400 focus:outline-none resize-none"
          />
        </div>
      </div>

      <div>
        <label className="text-xs font-medium text-gray-500 block mb-1">
          Send to
        </label>
        <input
          type="email"
          value={form.to}
          onChange={(e) => setForm((s) => ({ ...s, to: e.target.value }))}
          placeholder="recruiter@company.com"
          className="w-full rounded-md border border-gray-300 px-3 py-1.5 text-xs text-gray-900 placeholder-gray-400 focus:border-blue-400 focus:outline-none"
        />
      </div>

      <div className="flex gap-2">
        <button
          onClick={reset}
          className="flex-shrink-0 rounded-md border border-gray-200 px-3 py-2 text-xs text-gray-600 hover:bg-gray-50"
        >
          Back
        </button>
        <button
          onClick={() => void handleSend()}
          disabled={
            form.sending ||
            !form.to.trim() ||
            !form.subject.trim() ||
            !form.body.trim()
          }
          className="flex-1 rounded-md bg-blue-600 py-2 text-xs font-medium text-white hover:bg-blue-700 disabled:opacity-50"
        >
          {form.sending ? "Sending…" : "Send Application"}
        </button>
      </div>
    </div>
  );
}

// ── Sent screen ───────────────────────────────────────────────────────────────

function SentScreen() {
  const { reset } = useApplicationStore();
  return (
    <div className="flex flex-col items-center text-center py-4 gap-3">
      <div className="w-10 h-10 rounded-full bg-green-100 flex items-center justify-center">
        <svg
          className="w-5 h-5 text-green-600"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M5 13l4 4L19 7"
          />
        </svg>
      </div>
      <div>
        <p className="text-sm font-semibold text-gray-900">Application sent!</p>
        <p className="text-xs text-gray-500 mt-0.5">
          Your email is on its way.
        </p>
      </div>
      <button
        onClick={reset}
        className="rounded-md border border-gray-200 px-4 py-1.5 text-xs text-gray-600 hover:bg-gray-50"
      >
        Apply to another post
      </button>
    </div>
  );
}

// ── Main component ────────────────────────────────────────────────────────────

export default function AnalyseFlow() {
  const { state, startAnalysis, reset } = useApplicationStore();
  const { quota, load: loadQuota } = useQuotaStore();

  useEffect(() => {
    void loadQuota();
  }, [loadQuota]);

  const isDailyLimit =
    state.phase === "error" && state.message?.includes("analyses for today");

  if (state.phase === "extracting") {
    return (
      <div className="flex items-center gap-2 py-3">
        <Spinner />
        <p className="text-sm text-gray-500">Reading post…</p>
      </div>
    );
  }

  if (state.phase === "analysing") {
    return (
      <div className="flex items-center gap-2 py-3">
        <Spinner />
        <p className="text-sm text-gray-500">Analysing with AI…</p>
      </div>
    );
  }

  if (state.phase === "sending") {
    return (
      <div className="flex items-center gap-2 py-3">
        <Spinner />
        <p className="text-sm text-gray-500">Sending via Gmail…</p>
      </div>
    );
  }

  if (state.phase === "preview") {
    return <PreviewScreen job={state.job} draft={state.draft} />;
  }

  if (state.phase === "sent") {
    return <SentScreen />;
  }

  if (state.phase === "error") {
    if (isDailyLimit) {
      return (
        <div className="flex flex-col gap-2 py-1">
          <div className="rounded-lg border border-orange-200 bg-orange-50 px-3 py-3">
            <p className="text-sm font-semibold text-orange-700">
              Daily limit reached
            </p>
            <p className="text-xs text-orange-600 mt-1">{state.message}</p>
          </div>
          <button
            onClick={reset}
            className="text-xs text-gray-400 hover:text-gray-600 text-left"
          >
            Dismiss
          </button>
        </div>
      );
    }
    return (
      <div className="flex flex-col gap-2 py-1">
        <p className="text-sm text-red-600">{state.message}</p>
        <div className="flex gap-2">
          <button
            onClick={reset}
            className="text-xs text-gray-500 hover:text-gray-700"
          >
            Dismiss
          </button>
          <button
            onClick={() => void startAnalysis()}
            className="text-xs text-blue-600 hover:text-blue-800"
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  // idle
  const exhausted = quota !== null && quota.remaining === 0;

  return (
    <div>
      <QuotaBar />
      <p className="text-sm text-gray-500">
        Navigate to a LinkedIn hiring post, then click <strong>Analyse</strong>.
      </p>
      <button
        onClick={() => void startAnalysis()}
        disabled={exhausted}
        className="mt-3 w-full rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
      >
        Analyse Post
      </button>
      {exhausted && (
        <p className="mt-2 text-center text-xs text-orange-500">
          Daily limit reached — come back tomorrow
        </p>
      )}
    </div>
  );
}
