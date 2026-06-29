import type { FromServiceWorkerMessage } from "@/shared/messages";
import { extractPost } from "./post-extractor";

console.warn("[SmartApply] content script loaded on", window.location.hostname);

chrome.runtime.onMessage.addListener(
  (message: FromServiceWorkerMessage, _sender, sendResponse) => {
    if (message.type === "EXTRACT_POST") {
      sendResponse(extractPost());
    }
  },
);
