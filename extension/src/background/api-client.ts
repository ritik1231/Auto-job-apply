import { tokenStorage } from "@/storage/token-storage";
import type {
  ApplicationDraft,
  ApplicationHistoryItem,
  ApplicationSendResult,
  JobPost,
  Resume,
  ResumeListResponse,
  User,
} from "@/shared/types";

const API_BASE =
  import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000/api/v1";

interface ExchangeResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  user: User;
}

class ApiClient {
  private async request<T>(
    method: string,
    path: string,
    body?: unknown,
    retry = true,
  ): Promise<T> {
    const token = await tokenStorage.getAccessToken();
    const headers: Record<string, string> = {
      "Content-Type": "application/json",
    };
    if (token) headers["Authorization"] = `Bearer ${token}`;

    const res = await fetch(`${API_BASE}${path}`, {
      method,
      headers,
      body: body !== undefined ? JSON.stringify(body) : undefined,
    });

    if (res.status === 401 && retry) {
      const refreshed = await this._tryRefresh();
      if (refreshed) return this.request<T>(method, path, body, false);
      throw new Error("Authentication required");
    }

    if (!res.ok) {
      const err: unknown = await res.json().catch(() => ({}));
      throw new Error(
        (err as { error?: { message?: string } })?.error?.message ??
          `HTTP ${res.status}`,
      );
    }

    if (res.status === 204) return undefined as T;
    return res.json() as Promise<T>;
  }

  private async _tryRefresh(): Promise<boolean> {
    const stored = await tokenStorage.get();
    if (!stored?.refresh_token) return false;
    try {
      const data = await fetch(`${API_BASE}/auth/refresh`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ refresh_token: stored.refresh_token }),
      }).then((r) => r.json() as Promise<{ access_token: string }>);
      await tokenStorage.updateAccessToken(data.access_token);
      return true;
    } catch {
      await tokenStorage.clear();
      return false;
    }
  }

  // ── Auth ────────────────────────────────────────────────────────────────────

  async getAuthorizeUrl(
    redirectUri: string,
    codeChallenge: string,
  ): Promise<{ auth_url: string }> {
    const params = new URLSearchParams({
      redirect_uri: redirectUri,
      code_challenge: codeChallenge,
    });
    return this.request<{ auth_url: string }>(
      "GET",
      `/auth/google/authorize?${params.toString()}`,
      undefined,
      false,
    );
  }

  async exchangeCode(
    code: string,
    redirectUri: string,
    codeVerifier: string,
  ): Promise<ExchangeResponse> {
    return this.request<ExchangeResponse>(
      "POST",
      "/auth/exchange",
      { code, redirect_uri: redirectUri, code_verifier: codeVerifier },
      false,
    );
  }

  async getMe(): Promise<User> {
    return this.request<User>("GET", "/auth/me");
  }

  // ── Resumes ─────────────────────────────────────────────────────────────────

  async listResumes(): Promise<ResumeListResponse> {
    return this.request<ResumeListResponse>("GET", "/resumes/");
  }

  async uploadResume(file: File): Promise<Resume> {
    const token = await tokenStorage.getAccessToken();
    const headers: Record<string, string> = {};
    if (token) headers["Authorization"] = `Bearer ${token}`;

    const form = new FormData();
    form.append("file", file);

    const res = await fetch(`${API_BASE}/resumes/`, {
      method: "POST",
      headers,
      body: form,
    });

    if (res.status === 401) {
      const refreshed = await this._tryRefresh();
      if (refreshed) return this.uploadResume(file);
      throw new Error("Authentication required");
    }
    if (!res.ok) {
      const err: unknown = await res.json().catch(() => ({}));
      throw new Error(
        (err as { error?: { message?: string } })?.error?.message ??
          `HTTP ${res.status}`,
      );
    }
    return res.json() as Promise<Resume>;
  }

  async deleteResume(id: string): Promise<void> {
    return this.request<void>("DELETE", `/resumes/${id}`);
  }

  // ── Jobs & Applications ──────────────────────────────────────────────────────

  async extractJob(rawContent: string, sourceUrl?: string): Promise<JobPost> {
    return this.request<JobPost>("POST", "/jobs/extract", {
      raw_content: rawContent,
      source_url: sourceUrl ?? null,
      source_platform: "linkedin",
    });
  }

  async prepareApplication(jobPostId: string): Promise<ApplicationDraft> {
    return this.request<ApplicationDraft>("POST", "/applications/prepare", {
      job_post_id: jobPostId,
    });
  }

  async sendApplication(
    applicationId: string,
    toAddress?: string,
    subjectOverride?: string,
    bodyOverride?: string,
  ): Promise<ApplicationSendResult> {
    return this.request<ApplicationSendResult>(
      "POST",
      `/applications/${applicationId}/send`,
      {
        to_address: toAddress ?? null,
        subject_override: subjectOverride ?? null,
        body_override: bodyOverride ?? null,
      },
    );
  }

  async listApplicationHistory(
    limit = 20,
    offset = 0,
  ): Promise<ApplicationHistoryItem[]> {
    const params = new URLSearchParams({
      limit: String(limit),
      offset: String(offset),
    });
    return this.request<ApplicationHistoryItem[]>(
      "GET",
      `/applications/history?${params.toString()}`,
    );
  }
}

export const apiClient = new ApiClient();
