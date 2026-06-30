import { create } from "zustand";
import { apiClient } from "@/background/api-client";
import type { UserProfileUpdate } from "@/shared/types";

interface ProfileData {
  current_ctc: string;
  expected_ctc: string;
  notice_period: string;
  current_location: string;
  total_experience: string;
  linkedin_url: string;
  github_url: string;
  website_url: string;
}

interface ProfileState {
  profile: ProfileData;
  isLoading: boolean;
  isSaving: boolean;
  error: string | null;
}

interface ProfileActions {
  loadProfile: () => Promise<void>;
  saveProfile: (data: ProfileData) => Promise<void>;
}

const EMPTY: ProfileData = {
  current_ctc: "",
  expected_ctc: "",
  notice_period: "",
  current_location: "",
  total_experience: "",
  linkedin_url: "",
  github_url: "",
  website_url: "",
};

export const useProfileStore = create<ProfileState & ProfileActions>((set) => ({
  profile: EMPTY,
  isLoading: false,
  isSaving: false,
  error: null,

  loadProfile: async () => {
    set({ isLoading: true, error: null });
    try {
      const user = await apiClient.getMe();
      set({
        profile: {
          current_ctc: user.current_ctc ?? "",
          expected_ctc: user.expected_ctc ?? "",
          notice_period: user.notice_period ?? "",
          current_location: user.current_location ?? "",
          total_experience: user.total_experience ?? "",
          linkedin_url: user.linkedin_url ?? "",
          github_url: user.github_url ?? "",
          website_url: user.website_url ?? "",
        },
        isLoading: false,
      });
    } catch (err) {
      set({
        isLoading: false,
        error: err instanceof Error ? err.message : "Failed to load profile",
      });
    }
  },

  saveProfile: async (data: ProfileData) => {
    set({ isSaving: true, error: null });
    try {
      const payload: UserProfileUpdate = {
        current_ctc: data.current_ctc || null,
        expected_ctc: data.expected_ctc || null,
        notice_period: data.notice_period || null,
        current_location: data.current_location || null,
        total_experience: data.total_experience || null,
        linkedin_url: data.linkedin_url || null,
        github_url: data.github_url || null,
        website_url: data.website_url || null,
      };
      const user = await apiClient.updateProfile(payload);
      set({
        profile: {
          current_ctc: user.current_ctc ?? "",
          expected_ctc: user.expected_ctc ?? "",
          notice_period: user.notice_period ?? "",
          current_location: user.current_location ?? "",
          total_experience: user.total_experience ?? "",
          linkedin_url: user.linkedin_url ?? "",
          github_url: user.github_url ?? "",
          website_url: user.website_url ?? "",
        },
        isSaving: false,
      });
    } catch (err) {
      set({
        isSaving: false,
        error: err instanceof Error ? err.message : "Failed to save profile",
      });
    }
  },
}));
