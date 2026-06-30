import { useEffect, useState } from "react";
import { useProfileStore } from "@/popup/stores/profile-store";

type FieldKey =
  | "current_ctc"
  | "expected_ctc"
  | "notice_period"
  | "current_location"
  | "total_experience"
  | "linkedin_url"
  | "github_url"
  | "website_url";

interface Field {
  key: FieldKey;
  label: string;
  placeholder: string;
  type?: string;
}

const FIELDS: Field[] = [
  {
    key: "total_experience",
    label: "Total Experience",
    placeholder: "e.g. 5 years",
  },
  { key: "current_ctc", label: "Current CTC", placeholder: "e.g. 15 LPA" },
  { key: "expected_ctc", label: "Expected CTC", placeholder: "e.g. 18 LPA" },
  { key: "notice_period", label: "Notice Period", placeholder: "e.g. 30 days" },
  {
    key: "current_location",
    label: "Current Location",
    placeholder: "e.g. Bangalore",
  },
  {
    key: "linkedin_url",
    label: "LinkedIn",
    placeholder: "https://linkedin.com/in/yourname",
    type: "url",
  },
  {
    key: "github_url",
    label: "GitHub",
    placeholder: "https://github.com/yourname",
    type: "url",
  },
  {
    key: "website_url",
    label: "Website",
    placeholder: "https://yourwebsite.com",
    type: "url",
  },
];

const URL_KEYS = new Set<FieldKey>([
  "linkedin_url",
  "github_url",
  "website_url",
]);
const WIDE_KEYS = new Set<FieldKey>([
  "linkedin_url",
  "github_url",
  "website_url",
]);

export default function ProfilePanel() {
  const { profile, isLoading, isSaving, error, loadProfile, saveProfile } =
    useProfileStore();
  const [isOpen, setIsOpen] = useState(false);
  const [isExpanded, setIsExpanded] = useState(false);
  const [draft, setDraft] = useState(profile);

  useEffect(() => {
    void loadProfile();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    setDraft(profile);
  }, [profile]);

  function handleOpen() {
    setDraft(profile);
    setIsOpen(true);
  }

  async function handleSave() {
    await saveProfile(draft);
    setIsOpen(false);
  }

  const filledCount = Object.values(profile).filter(Boolean).length;
  const hasData = filledCount > 0;

  return (
    <div className="mt-3">
      <div className="flex items-center justify-between mb-1.5">
        <button
          onClick={() => hasData && !isOpen && setIsExpanded((e) => !e)}
          className="flex items-center gap-1 text-xs font-semibold uppercase tracking-wide text-gray-500 hover:text-gray-700 disabled:cursor-default disabled:hover:text-gray-500"
          disabled={!hasData || isOpen}
        >
          <span>Additional Info</span>
          {hasData && !isOpen && (
            <svg
              className={`w-3 h-3 transition-transform duration-150 ${isExpanded ? "rotate-180" : ""}`}
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2.5}
                d="M19 9l-7 7-7-7"
              />
            </svg>
          )}
        </button>
        <button
          onClick={isOpen ? () => setIsOpen(false) : handleOpen}
          className="text-xs text-blue-600 hover:text-blue-800"
        >
          {isOpen ? "Cancel" : hasData ? "Edit" : "Add"}
        </button>
      </div>

      {isLoading ? (
        <p className="text-xs text-gray-400 py-2 text-center">Loading…</p>
      ) : isOpen ? (
        <div className="rounded-lg border border-gray-200 bg-gray-50 px-3 py-3 space-y-2.5">
          {FIELDS.map(({ key, label, placeholder, type }) => (
            <div key={key}>
              <label className="block text-xs font-medium text-gray-600 mb-0.5">
                {label}
              </label>
              <input
                type={type ?? "text"}
                value={draft[key]}
                placeholder={placeholder}
                onChange={(e) =>
                  setDraft((d) => ({ ...d, [key]: e.target.value }))
                }
                className="w-full rounded border border-gray-200 bg-white px-2 py-1.5 text-xs text-gray-800 placeholder-gray-400 focus:border-blue-400 focus:outline-none"
              />
            </div>
          ))}
          {error && <p className="text-xs text-red-600">{error}</p>}
          <button
            onClick={() => void handleSave()}
            disabled={isSaving}
            className="w-full mt-1 rounded-md bg-blue-600 py-1.5 text-xs font-medium text-white hover:bg-blue-700 disabled:opacity-50"
          >
            {isSaving ? "Saving…" : "Save"}
          </button>
        </div>
      ) : isExpanded && hasData ? (
        <div className="rounded-lg border border-gray-200 bg-gray-50 px-3 py-2.5">
          <dl className="grid grid-cols-2 gap-x-4 gap-y-1.5">
            {FIELDS.filter(({ key }) => profile[key]).map(({ key, label }) => (
              <div key={key} className={WIDE_KEYS.has(key) ? "col-span-2" : ""}>
                <dt className="text-[10px] text-gray-400">{label}</dt>
                <dd className="text-xs font-medium text-gray-800 truncate">
                  {URL_KEYS.has(key) ? (
                    <a
                      href={profile[key]}
                      target="_blank"
                      rel="noreferrer"
                      className="text-blue-600 hover:underline"
                    >
                      {profile[key]}
                    </a>
                  ) : (
                    profile[key]
                  )}
                </dd>
              </div>
            ))}
          </dl>
        </div>
      ) : !hasData ? (
        <button
          onClick={handleOpen}
          className="w-full rounded-lg border border-dashed border-gray-300 py-3 text-center text-xs text-gray-400 hover:border-blue-400 hover:text-blue-500 transition-colors"
        >
          Add CTC, experience, LinkedIn…
        </button>
      ) : null}
    </div>
  );
}
