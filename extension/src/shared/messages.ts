import type { User } from "@/shared/types";

// ── Content script protocol ───────────────────────────────────────────────────

/** Sent from the service worker to the content script. */
export type ExtractPostMessage = { type: "EXTRACT_POST" };

/** Sent back from the content script on success. */
export type PostExtractedMessage = { type: "POST_EXTRACTED"; text: string };

/** Sent back from the content script on failure. */
export type ExtractionErrorMessage = {
  type: "EXTRACTION_ERROR";
  reason: string;
};

/** Union of all responses the content script can return. */
export type ContentScriptResponse =
  PostExtractedMessage | ExtractionErrorMessage;

/** POST_EXTRACTED forwarded to the popup — augmented with the tab URL by the service worker. */
export type PostExtractedResponse = {
  type: "POST_EXTRACTED";
  text: string;
  url: string;
};

// ── Popup → Service Worker messages ──────────────────────────────────────────

export type InitiateAuthMessage = { type: "INITIATE_AUTH" };
export type GetAuthStateMessage = { type: "GET_AUTH_STATE" };
export type LogoutMessage = { type: "LOGOUT" };

/** Union of all messages the popup can send to the service worker. */
export type PopupToWorkerMessage =
  | ExtractPostMessage
  | InitiateAuthMessage
  | GetAuthStateMessage
  | LogoutMessage;

// ── Service Worker → Popup responses ─────────────────────────────────────────

export type AuthSuccessResponse = { type: "AUTH_SUCCESS"; user: User };
export type AuthErrorResponse = { type: "AUTH_ERROR"; reason: string };
export type AuthStateResponse = {
  type: "AUTH_STATE";
  isAuthenticated: boolean;
  user: User | null;
};
export type LogoutCompleteResponse = { type: "LOGOUT_COMPLETE" };

export type WorkerResponse =
  | PostExtractedResponse
  | ExtractionErrorMessage
  | AuthSuccessResponse
  | AuthErrorResponse
  | AuthStateResponse
  | LogoutCompleteResponse;

// Legacy alias — kept so content/index.ts compiles unchanged
export type FromServiceWorkerMessage = ExtractPostMessage;
