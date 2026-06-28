"""Input sanitization utilities.

All functions are pure (no I/O) and safe to call before hashing or AI processing.
"""

from __future__ import annotations

import html
import os
import re

_HTML_TAG_RE = re.compile(r"<[^>]+>", re.DOTALL)
_MULTI_SPACES_RE = re.compile(r"[ \t]+")
_MANY_NEWLINES_RE = re.compile(r"\n{3,}")
_UNSAFE_FILENAME_RE = re.compile(r"[^\w\s.\-]")
_WHITESPACE_RE = re.compile(r"[\s_]+")
_EMAIL_RE = re.compile(r"^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$")


def sanitize_post_text(text: str) -> str:
    """Strip HTML tags, decode entities, collapse excess whitespace.

    Preserves newlines so paragraph structure is kept for the AI.
    Safe to call before hashing — identical posts with/without HTML get the same hash.
    """
    text = _HTML_TAG_RE.sub(" ", text)
    text = html.unescape(text)
    text = _MULTI_SPACES_RE.sub(" ", text)
    text = _MANY_NEWLINES_RE.sub("\n\n", text)
    return text.strip()


def sanitize_filename(filename: str) -> str:
    """Return a safe display name — no path traversal, no special characters.

    The actual stored file always uses a UUID path; this is only the label
    persisted in the database and shown in the UI.
    """
    name = os.path.basename(filename)
    name = _UNSAFE_FILENAME_RE.sub("_", name)
    name = _WHITESPACE_RE.sub("_", name)
    name = name.strip("._-")[:255]
    return name or "resume.pdf"


def is_valid_email(value: str) -> bool:
    """Light-weight email format check (not RFC-exhaustive, good enough for UI validation)."""
    return bool(_EMAIL_RE.match(value.strip()))
