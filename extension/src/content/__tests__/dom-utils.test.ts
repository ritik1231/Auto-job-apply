import { describe, it, expect, beforeEach } from "vitest";
import {
  normalizeText,
  extractVisibleText,
  queryFirst,
  isTruncated,
} from "../dom-utils";

describe("normalizeText", () => {
  it("collapses multiple spaces to one", () => {
    expect(normalizeText("hello   world")).toBe("hello world");
  });

  it("collapses tabs to a single space", () => {
    expect(normalizeText("a\t\tb")).toBe("a b");
  });

  it("trims leading and trailing whitespace", () => {
    expect(normalizeText("  hello  ")).toBe("hello");
  });

  it("collapses 3+ consecutive newlines to 2", () => {
    expect(normalizeText("a\n\n\n\nb")).toBe("a\n\nb");
  });

  it("preserves double newlines (paragraph breaks)", () => {
    expect(normalizeText("para one\n\npara two")).toBe("para one\n\npara two");
  });

  it("returns empty string for blank input", () => {
    expect(normalizeText("   ")).toBe("");
  });
});

describe("extractVisibleText", () => {
  beforeEach(() => {
    document.body.innerHTML = "";
  });

  it("returns normalised textContent of an element", () => {
    const el = document.createElement("div");
    el.textContent = "  Hello   World  ";
    expect(extractVisibleText(el)).toBe("Hello World");
  });

  it("returns empty string for an element with no text", () => {
    const el = document.createElement("div");
    expect(extractVisibleText(el)).toBe("");
  });
});

describe("queryFirst", () => {
  beforeEach(() => {
    document.body.innerHTML = "";
  });

  it("returns the first matching element", () => {
    document.body.innerHTML = '<div class="a"></div>';
    expect(queryFirst([".b", ".a"])).not.toBeNull();
  });

  it("returns null when nothing matches", () => {
    expect(queryFirst([".x", ".y"])).toBeNull();
  });

  it("respects priority — first selector wins", () => {
    document.body.innerHTML =
      '<div class="a" data-id="a"></div><div class="b" data-id="b"></div>';
    const result = queryFirst([".a", ".b"]);
    expect(result?.getAttribute("data-id")).toBe("a");
  });
});

describe("isTruncated", () => {
  it("detects trailing ellipsis", () => {
    expect(isTruncated("We are hiring…")).toBe(true);
  });

  it("detects ellipsis followed by whitespace", () => {
    expect(isTruncated("some text…  ")).toBe(true);
  });

  it("returns false for complete text", () => {
    expect(isTruncated("Send your CV to hello@example.com")).toBe(false);
  });

  it("returns false for text ending with a period", () => {
    expect(isTruncated("Apply today.")).toBe(false);
  });
});
