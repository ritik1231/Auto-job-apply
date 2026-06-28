import type { ContentScriptResponse } from "@/shared/messages";
import { extractVisibleText, queryMostVisible } from "./dom-utils";

/**
 * CSS selectors tried in priority order.
 *
 * LinkedIn restructures class names frequently — prefer stable data-testid
 * attributes first, fall back to structural class names.
 */
const POST_TEXT_SELECTORS = [
  // Stable test ID — confirmed present in 2025 LinkedIn DOM
  '[data-testid="expandable-text-box"]',
  // Permalink / feed update page variants
  '[data-testid="post-text"]',
  '[data-testid="main-feed-activity-card-text"]',
  // Older class-based selectors kept as fallbacks
  ".update-components-text__text-view",
  ".update-components-text",
  ".feed-shared-update-v2 .feed-shared-text .break-words",
  ".update-components-text .break-words",
  ".feed-shared-update-v2 .break-words",
  ".feed-shared-update-v2__content .break-words",
  ".feed-shared-update-v2__description",
  ".attributed-text-segment-list__content",
  ".feed-shared-text",
] as const;

/** Posts shorter than this are likely navigation elements, not job posts. */
const MIN_TEXT_LENGTH = 50;

export function extractPost(): ContentScriptResponse {
  const el = queryMostVisible(POST_TEXT_SELECTORS);

  if (!el) {
    return {
      type: "EXTRACTION_ERROR",
      reason:
        "No LinkedIn post found on this page. Navigate to a hiring post and try again.",
    };
  }

  const text = extractVisibleText(el);

  if (text.length < MIN_TEXT_LENGTH) {
    return {
      type: "EXTRACTION_ERROR",
      reason: "Extracted text is too short — this may not be a job post.",
    };
  }

  return { type: "POST_EXTRACTED", text };
}
