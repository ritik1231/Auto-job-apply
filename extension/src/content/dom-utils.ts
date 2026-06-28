const ZERO_WIDTH_RE = /[\u200B\uFEFF\u00AD]/g;
const INLINE_WHITESPACE_RE = /[ \t]+/g;
const EXCESS_NEWLINES_RE = /\n{3,}/g;

/** Clean raw text: remove zero-width chars, collapse whitespace, normalise newlines. */
export function normalizeText(raw: string): string {
  return raw
    .replace(ZERO_WIDTH_RE, "")
    .replace(INLINE_WHITESPACE_RE, " ")
    .replace(EXCESS_NEWLINES_RE, "\n\n")
    .trim();
}

/** Extract and normalise the visible text from a DOM element. */
export function extractVisibleText(el: Element): string {
  return normalizeText(el.textContent ?? "");
}

/**
 * Return the first element that matches any selector in the priority list,
 * or null if none match.
 */
export function queryFirst(selectors: readonly string[]): Element | null {
  for (const sel of selectors) {
    const el = document.querySelector(sel);
    if (el) return el;
  }
  return null;
}

/**
 * Return the element (across all candidates for the given selectors) that has
 * the most pixels visible inside the current viewport.
 *
 * Why visible-area beats center-distance:
 *   Center-distance breaks at post boundaries — if two posts each occupy half
 *   the viewport, their centers are equidistant and the wrong one can win.
 *   Visible area is unambiguous: the post the user is actually reading has more
 *   of its pixels on-screen than any partially-scrolled neighbour.
 *
 * Tiebreaker: prefer the element whose top edge is higher in the viewport
 * (i.e. the one the user reached first while scrolling).
 */
export function queryMostVisible(selectors: readonly string[]): Element | null {
  let candidates: Element[] = [];
  for (const sel of selectors) {
    const found = Array.from(document.querySelectorAll(sel));
    if (found.length > 0) {
      candidates = found;
      break; // use only the first selector that yields results (priority order)
    }
  }
  if (candidates.length === 0) return null;
  if (candidates.length === 1) return candidates[0];

  const viewportH = window.innerHeight;
  let best: Element | null = null;
  let bestVisiblePx = -1;
  let bestTop = Infinity;

  for (const el of candidates) {
    const rect = el.getBoundingClientRect();
    if (rect.height === 0) continue;
    // pixels of this element that are inside [0, viewportH]
    const visibleTop = Math.max(rect.top, 0);
    const visibleBottom = Math.min(rect.bottom, viewportH);
    const visiblePx = Math.max(0, visibleBottom - visibleTop);

    if (
      visiblePx > bestVisiblePx ||
      (visiblePx === bestVisiblePx && rect.top < bestTop)
    ) {
      bestVisiblePx = visiblePx;
      bestTop = rect.top;
      best = el;
    }
  }

  // Nothing is in the viewport at all — fall back to the topmost element
  return best ?? candidates[0];
}

/** True when LinkedIn has truncated the post with a "see more" ellipsis suffix. */
export function isTruncated(text: string): boolean {
  return /\u2026\s*$/.test(text);
}
