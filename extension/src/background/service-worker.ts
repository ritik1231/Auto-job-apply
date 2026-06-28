import type {
  ContentScriptResponse,
  ExtractPostMessage,
  PostExtractedResponse,
  WorkerResponse,
  PopupToWorkerMessage,
} from "@/shared/messages";
import { initiateOAuthFlow } from "./auth-flow";
import { tokenStorage } from "@/storage/token-storage";

chrome.runtime.onInstalled.addListener(() => {
  console.warn("[AIJobApply] extension installed");
});

chrome.runtime.onStartup.addListener(() => {
  console.warn("[AIJobApply] service worker started");
});

// ── Message handler ───────────────────────────────────────────────────────────

chrome.runtime.onMessage.addListener(
  (
    message: PopupToWorkerMessage,
    _sender,
    sendResponse: (r: WorkerResponse) => void,
  ) => {
    switch (message.type) {
      case "EXTRACT_POST":
        handleExtractPost(sendResponse);
        return true;

      case "INITIATE_AUTH":
        handleInitiateAuth(sendResponse);
        return true;

      case "GET_AUTH_STATE":
        handleGetAuthState(sendResponse);
        return true;

      case "LOGOUT":
        handleLogout(sendResponse);
        return true;
    }
  },
);

// ── Handlers ──────────────────────────────────────────────────────────────────

function handleExtractPost(sendResponse: (r: WorkerResponse) => void): void {
  chrome.tabs.query({ active: true, lastFocusedWindow: true }, (tabs) => {
    const tab = tabs[0];
    if (!tab?.id) {
      sendResponse({ type: "EXTRACTION_ERROR", reason: "No active tab found" });
      return;
    }

    chrome.tabs.sendMessage(
      tab.id,
      { type: "EXTRACT_POST" } satisfies ExtractPostMessage,
      (response: ContentScriptResponse) => {
        if (chrome.runtime.lastError) {
          sendResponse({
            type: "EXTRACTION_ERROR",
            reason:
              chrome.runtime.lastError.message ??
              "Content script not available on this page",
          });
          return;
        }
        console.warn("[AIJobApply] extraction result:", response.type);
        if (response.type === "POST_EXTRACTED") {
          sendResponse({
            type: "POST_EXTRACTED",
            text: response.text,
            url: tab.url ?? "",
          } satisfies PostExtractedResponse);
        } else {
          sendResponse(response);
        }
      },
    );
  });
}

function handleInitiateAuth(sendResponse: (r: WorkerResponse) => void): void {
  initiateOAuthFlow()
    .then((user) => sendResponse({ type: "AUTH_SUCCESS", user }))
    .catch((err: unknown) =>
      sendResponse({
        type: "AUTH_ERROR",
        reason: err instanceof Error ? err.message : "Authentication failed",
      }),
    );
}

function handleGetAuthState(sendResponse: (r: WorkerResponse) => void): void {
  tokenStorage
    .get()
    .then((stored) =>
      sendResponse({
        type: "AUTH_STATE",
        isAuthenticated: stored !== null,
        user: stored?.user ?? null,
      }),
    )
    .catch(() =>
      sendResponse({ type: "AUTH_STATE", isAuthenticated: false, user: null }),
    );
}

function handleLogout(sendResponse: (r: WorkerResponse) => void): void {
  tokenStorage
    .clear()
    .then(() => sendResponse({ type: "LOGOUT_COMPLETE" }))
    .catch(() => sendResponse({ type: "LOGOUT_COMPLETE" }));
}
