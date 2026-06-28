import { create } from "zustand";
import { apiClient } from "@/background/api-client";
import type { ApplicationHistoryItem } from "@/shared/types";

interface HistoryState {
  items: ApplicationHistoryItem[];
  isLoading: boolean;
  error: string | null;
}

interface HistoryActions {
  load: () => Promise<void>;
}

export const useHistoryStore = create<HistoryState & HistoryActions>((set) => ({
  items: [],
  isLoading: false,
  error: null,

  load: async () => {
    set({ isLoading: true, error: null });
    try {
      const items = await apiClient.listApplicationHistory();
      set({ items, isLoading: false });
    } catch (err) {
      set({
        isLoading: false,
        error: err instanceof Error ? err.message : "Failed to load history",
      });
    }
  },
}));
