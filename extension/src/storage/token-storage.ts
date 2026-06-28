import type { User } from "@/shared/types";

interface StoredAuth {
  access_token: string;
  refresh_token: string;
  user: User;
}

const KEY = "auth";

export const tokenStorage = {
  async get(): Promise<StoredAuth | null> {
    const result = await chrome.storage.local.get(KEY);
    return (result[KEY] as StoredAuth) ?? null;
  },

  async set(data: StoredAuth): Promise<void> {
    await chrome.storage.local.set({ [KEY]: data });
  },

  async clear(): Promise<void> {
    await chrome.storage.local.remove(KEY);
  },

  async getAccessToken(): Promise<string | null> {
    return (await this.get())?.access_token ?? null;
  },

  async updateAccessToken(access_token: string): Promise<void> {
    const stored = await this.get();
    if (stored) await this.set({ ...stored, access_token });
  },
};
