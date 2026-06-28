import { create } from "zustand";
import type { User } from "@/shared/types";
import type { WorkerResponse } from "@/shared/messages";

interface AuthState {
  isAuthenticated: boolean;
  user: User | null;
  isLoading: boolean;
  error: string | null;
}

interface AuthActions {
  signIn: () => Promise<void>;
  signOut: () => Promise<void>;
  checkAuth: () => Promise<void>;
}

function sendWorkerMessage(type: string): Promise<WorkerResponse> {
  return new Promise((resolve, reject) => {
    chrome.runtime.sendMessage({ type }, (response: WorkerResponse) => {
      if (chrome.runtime.lastError) {
        reject(
          new Error(
            chrome.runtime.lastError.message ?? "Service worker unreachable",
          ),
        );
      } else {
        resolve(response);
      }
    });
  });
}

export const useAuthStore = create<AuthState & AuthActions>((set) => ({
  isAuthenticated: false,
  user: null,
  isLoading: false,
  error: null,

  signIn: async () => {
    set({ isLoading: true, error: null });
    try {
      const response = await sendWorkerMessage("INITIATE_AUTH");
      if (response.type === "AUTH_SUCCESS") {
        set({ isAuthenticated: true, user: response.user, isLoading: false });
      } else if (response.type === "AUTH_ERROR") {
        set({ isLoading: false, error: response.reason });
      }
    } catch (err) {
      set({
        isLoading: false,
        error: err instanceof Error ? err.message : "Sign-in failed",
      });
    }
  },

  signOut: async () => {
    try {
      await sendWorkerMessage("LOGOUT");
    } finally {
      set({ isAuthenticated: false, user: null, error: null });
    }
  },

  checkAuth: async () => {
    set({ isLoading: true });
    try {
      const response = await sendWorkerMessage("GET_AUTH_STATE");
      if (response.type === "AUTH_STATE") {
        set({
          isAuthenticated: response.isAuthenticated,
          user: response.user,
          isLoading: false,
        });
      }
    } catch {
      set({ isLoading: false });
    }
  },
}));
