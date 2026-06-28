import { apiClient } from "./api-client";
import { tokenStorage } from "@/storage/token-storage";
import type { User } from "@/shared/types";

function launchWebAuthFlow(url: string): Promise<string> {
  return new Promise((resolve, reject) => {
    chrome.identity.launchWebAuthFlow(
      { url, interactive: true },
      (callbackUrl) => {
        if (chrome.runtime.lastError || !callbackUrl) {
          reject(
            new Error(
              chrome.runtime.lastError?.message ?? "Auth flow was cancelled",
            ),
          );
        } else {
          resolve(callbackUrl);
        }
      },
    );
  });
}

function base64urlEncode(buffer: ArrayBuffer): string {
  return btoa(String.fromCharCode(...new Uint8Array(buffer)))
    .replace(/\+/g, "-")
    .replace(/\//g, "_")
    .replace(/=/g, "");
}

function generateCodeVerifier(): string {
  const bytes = new Uint8Array(32);
  crypto.getRandomValues(bytes);
  return base64urlEncode(bytes.buffer);
}

async function generateCodeChallenge(verifier: string): Promise<string> {
  const data = new TextEncoder().encode(verifier);
  const hash = await crypto.subtle.digest("SHA-256", data);
  return base64urlEncode(hash);
}

/**
 * Full OAuth dance with PKCE:
 * 1. Generate code_verifier + code_challenge (S256)
 * 2. Get auth URL from backend with code_challenge embedded
 * 3. Launch Google auth in a popup via chrome.identity
 * 4. Extract the authorization code from the callback URL
 * 5. Exchange code + code_verifier for JWT tokens + user via backend
 * 6. Persist to chrome.storage.local
 * Returns the authenticated user.
 */
export async function initiateOAuthFlow(): Promise<User> {
  const redirectUri = chrome.identity.getRedirectURL();
  const codeVerifier = generateCodeVerifier();
  const codeChallenge = await generateCodeChallenge(codeVerifier);

  const { auth_url } = await apiClient.getAuthorizeUrl(
    redirectUri,
    codeChallenge,
  );
  const callbackUrl = await launchWebAuthFlow(auth_url);

  const code = new URL(callbackUrl).searchParams.get("code");
  if (!code) throw new Error("No authorization code in OAuth callback URL");

  const { access_token, refresh_token, user } = await apiClient.exchangeCode(
    code,
    redirectUri,
    codeVerifier,
  );
  await tokenStorage.set({ access_token, refresh_token, user });

  return user;
}
