import { create } from "zustand";
import { apiClient } from "@/background/api-client";
import type { QuotaInfo } from "@/shared/types";

interface QuotaState {
  quota: QuotaInfo | null;
  isLoading: boolean;
  load: () => Promise<void>;
  invalidate: () => void;
}

export const useQuotaStore = create<QuotaState>((set) => ({
  quota: null,
  isLoading: false,

  load: async () => {
    set({ isLoading: true });
    try {
      const quota = await apiClient.getQuota();
      set({ quota, isLoading: false });
    } catch {
      set({ isLoading: false });
    }
  },

  invalidate: () => set({ quota: null }),
}));
