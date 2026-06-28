import { create } from "zustand";
import { apiClient } from "@/background/api-client";
import type {
  ApplicationDraft,
  ApplicationSendResult,
  JobPost,
} from "@/shared/types";
import type { WorkerResponse } from "@/shared/messages";

type AnalysisState =
  | { phase: "idle" }
  | { phase: "extracting" }
  | { phase: "analysing" }
  | { phase: "preview"; job: JobPost; draft: ApplicationDraft }
  | { phase: "sending"; job: JobPost; draft: ApplicationDraft }
  | { phase: "sent"; result: ApplicationSendResult }
  | { phase: "error"; message: string };

interface ApplicationStoreState {
  state: AnalysisState;
  startAnalysis: () => Promise<void>;
  sendApplication: (
    toAddress?: string,
    subjectOverride?: string,
    bodyOverride?: string,
  ) => Promise<void>;
  reset: () => void;
}

function sendExtractMessage(): Promise<{ text: string; url: string }> {
  return new Promise((resolve, reject) => {
    chrome.runtime.sendMessage(
      { type: "EXTRACT_POST" },
      (response: WorkerResponse) => {
        if (chrome.runtime.lastError) {
          reject(
            new Error(
              chrome.runtime.lastError.message ?? "Service worker unreachable",
            ),
          );
          return;
        }
        if (response.type === "POST_EXTRACTED") {
          resolve({ text: response.text, url: response.url });
        } else if (response.type === "EXTRACTION_ERROR") {
          reject(new Error(response.reason));
        } else {
          reject(new Error("Unexpected response from service worker"));
        }
      },
    );
  });
}

export const useApplicationStore = create<ApplicationStoreState>(
  (set, get) => ({
    state: { phase: "idle" },

    startAnalysis: async () => {
      set({ state: { phase: "extracting" } });
      try {
        const { text, url } = await sendExtractMessage();

        set({ state: { phase: "analysing" } });
        const job = await apiClient.extractJob(text, url);
        const draft = await apiClient.prepareApplication(job.id);

        set({ state: { phase: "preview", job, draft } });
      } catch (err) {
        set({
          state: {
            phase: "error",
            message: err instanceof Error ? err.message : "Analysis failed",
          },
        });
      }
    },

    sendApplication: async (
      toAddress?: string,
      subjectOverride?: string,
      bodyOverride?: string,
    ) => {
      const current = get().state;
      if (current.phase !== "preview") return;

      const { job, draft } = current;
      set({ state: { phase: "sending", job, draft } });
      try {
        const result = await apiClient.sendApplication(
          draft.id,
          toAddress,
          subjectOverride,
          bodyOverride,
        );
        set({ state: { phase: "sent", result } });
      } catch (err) {
        set({
          state: {
            phase: "error",
            message: err instanceof Error ? err.message : "Send failed",
          },
        });
      }
    },

    reset: () => set({ state: { phase: "idle" } }),
  }),
);
