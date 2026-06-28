import { describe, it, expect, beforeEach } from "vitest";
import { extractPost } from "../post-extractor";

const SAMPLE_JOB_TEXT = `
  We are looking for a Senior Python Engineer to join our team at Acme Corp.
  Requirements: 5+ years Python, FastAPI, PostgreSQL, Docker.
  Please send your CV to john@acme.com or DM me directly.
`;

function buildPost(text: string, ...classChain: string[]) {
  let parent = document.body;
  for (const cls of classChain) {
    const el = document.createElement("div");
    el.className = cls;
    parent.appendChild(el);
    parent = el;
  }
  parent.textContent = text;
}

describe("extractPost", () => {
  beforeEach(() => {
    document.body.innerHTML = "";
  });

  it("extracts text from a standard feed post", () => {
    buildPost(
      SAMPLE_JOB_TEXT,
      "feed-shared-update-v2",
      "feed-shared-text",
      "break-words",
    );
    const result = extractPost();
    expect(result.type).toBe("POST_EXTRACTED");
    if (result.type === "POST_EXTRACTED") {
      expect(result.text).toContain("Senior Python Engineer");
      expect(result.text).toContain("Acme Corp");
      expect(result.text).toContain("john@acme.com");
    }
  });

  it("extracts text from the newer update-components format", () => {
    buildPost(SAMPLE_JOB_TEXT, "update-components-text", "break-words");
    const result = extractPost();
    expect(result.type).toBe("POST_EXTRACTED");
  });

  it("extracts text from a feed post without inner text wrapper", () => {
    buildPost(SAMPLE_JOB_TEXT, "feed-shared-update-v2", "break-words");
    const result = extractPost();
    expect(result.type).toBe("POST_EXTRACTED");
  });

  it("returns EXTRACTION_ERROR when no post element is found", () => {
    document.body.innerHTML = '<div class="some-other-page">Not a post</div>';
    const result = extractPost();
    expect(result.type).toBe("EXTRACTION_ERROR");
    if (result.type === "EXTRACTION_ERROR") {
      expect(result.reason).toMatch(/No LinkedIn post found/);
    }
  });

  it("returns EXTRACTION_ERROR when extracted text is too short", () => {
    buildPost(
      "Hiring!",
      "feed-shared-update-v2",
      "feed-shared-text",
      "break-words",
    );
    const result = extractPost();
    expect(result.type).toBe("EXTRACTION_ERROR");
    if (result.type === "EXTRACTION_ERROR") {
      expect(result.reason).toMatch(/too short/);
    }
  });

  it("normalises whitespace in the extracted text", () => {
    buildPost(
      "  We  are   hiring   a   Python   engineer   at   Acme   Corp.   Requirements include lots of experience.   ",
      "feed-shared-update-v2",
      "feed-shared-text",
      "break-words",
    );
    const result = extractPost();
    expect(result.type).toBe("POST_EXTRACTED");
    if (result.type === "POST_EXTRACTED") {
      expect(result.text).not.toMatch(/ {2}/); // no double spaces
    }
  });

  it("tries selectors in priority order and takes the first match", () => {
    // Set up both a high-priority and low-priority element
    buildPost(SAMPLE_JOB_TEXT, "update-components-text", "break-words");
    buildPost(
      "Different text from lower priority selector",
      "feed-shared-update-v2",
      "break-words",
    );
    // update-components-text comes before feed-shared-update-v2 in the selector list
    const result = extractPost();
    expect(result.type).toBe("POST_EXTRACTED");
    if (result.type === "POST_EXTRACTED") {
      expect(result.text).toContain("Senior Python Engineer"); // came from first selector
    }
  });
});
