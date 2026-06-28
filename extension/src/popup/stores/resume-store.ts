import { create } from "zustand";
import { apiClient } from "@/background/api-client";
import type { Resume } from "@/shared/types";

interface ResumeState {
  resumes: Resume[];
  activeId: string | null;
  isLoading: boolean;
  isUploading: boolean;
  error: string | null;
}

interface ResumeActions {
  loadResumes: () => Promise<void>;
  uploadResume: (file: File) => Promise<void>;
  deleteResume: (id: string) => Promise<void>;
}

export const useResumeStore = create<ResumeState & ResumeActions>(
  (set, get) => ({
    resumes: [],
    activeId: null,
    isLoading: false,
    isUploading: false,
    error: null,

    loadResumes: async () => {
      set({ isLoading: true, error: null });
      try {
        const { resumes, active_id } = await apiClient.listResumes();
        set({ resumes, activeId: active_id, isLoading: false });
      } catch (err) {
        set({
          isLoading: false,
          error: err instanceof Error ? err.message : "Failed to load resumes",
        });
      }
    },

    uploadResume: async (file: File) => {
      set({ isUploading: true, error: null });
      try {
        await apiClient.uploadResume(file);
        await get().loadResumes();
      } catch (err) {
        set({ error: err instanceof Error ? err.message : "Upload failed" });
      } finally {
        set({ isUploading: false });
      }
    },

    deleteResume: async (id: string) => {
      set({ error: null });
      try {
        await apiClient.deleteResume(id);
        await get().loadResumes();
      } catch (err) {
        set({ error: err instanceof Error ? err.message : "Delete failed" });
      }
    },
  }),
);
