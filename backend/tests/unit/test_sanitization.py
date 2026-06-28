"""Unit tests for app.core.sanitization — pure-function coverage."""

from __future__ import annotations

import pytest

from app.core.sanitization import is_valid_email, sanitize_filename, sanitize_post_text

# ── sanitize_post_text ────────────────────────────────────────────────────────


@pytest.mark.unit
def test_plain_text_unchanged():
    text = "We are hiring a Python engineer."
    assert sanitize_post_text(text) == text


@pytest.mark.unit
def test_html_tags_removed():
    result = sanitize_post_text("<p>We are <b>hiring</b> a Python engineer.</p>")
    assert "<" not in result
    assert ">" not in result
    assert "hiring" in result
    assert "Python engineer" in result


@pytest.mark.unit
def test_html_entity_decoded():
    result = sanitize_post_text("5&amp;10 years &amp; Python &lt;3")
    assert "&amp;" not in result
    assert "&lt;" not in result
    assert "5&10 years & Python" in result


@pytest.mark.unit
def test_multiple_spaces_collapsed():
    result = sanitize_post_text("Hiring   a   senior   engineer")
    assert "  " not in result
    assert result == "Hiring a senior engineer"


@pytest.mark.unit
def test_excess_newlines_collapsed():
    result = sanitize_post_text("Line one\n\n\n\n\nLine two")
    assert "\n\n\n" not in result
    assert "Line one" in result
    assert "Line two" in result


@pytest.mark.unit
def test_leading_trailing_whitespace_stripped():
    assert sanitize_post_text("  hello world  ") == "hello world"


@pytest.mark.unit
def test_empty_string_returns_empty():
    assert sanitize_post_text("") == ""


@pytest.mark.unit
def test_html_with_entities_produces_same_output_as_plain():
    """Same logical content with vs without HTML should produce identical text.

    This is the deduplication invariant — sanitize before hashing.
    """
    html_version = "<p>We are hiring a <strong>Python</strong> engineer.</p>"
    plain_version = "We are hiring a Python engineer."
    assert sanitize_post_text(html_version) == sanitize_post_text(plain_version)


@pytest.mark.unit
def test_multiline_html_stripped_preserves_paragraphs():
    text = "<p>Responsibilities:</p>\n<ul><li>Build APIs</li><li>Write tests</li></ul>"
    result = sanitize_post_text(text)
    assert "<" not in result
    assert "Responsibilities" in result
    assert "Build APIs" in result


# ── sanitize_filename ─────────────────────────────────────────────────────────


@pytest.mark.unit
def test_normal_filename_unchanged():
    assert sanitize_filename("resume.pdf") == "resume.pdf"


@pytest.mark.unit
def test_path_traversal_stripped():
    assert "/" not in sanitize_filename("../../etc/passwd")
    assert "\\" not in sanitize_filename("..\\windows\\system32\\file")


@pytest.mark.unit
def test_special_chars_replaced_with_underscore():
    result = sanitize_filename("my resume (2024)!.pdf")
    assert "(" not in result
    assert ")" not in result
    assert "!" not in result


@pytest.mark.unit
def test_whitespace_replaced_with_underscore():
    result = sanitize_filename("my resume 2024.pdf")
    assert " " not in result
    assert result == "my_resume_2024.pdf"


@pytest.mark.unit
def test_empty_filename_returns_default():
    assert sanitize_filename("") == "resume.pdf"


@pytest.mark.unit
def test_filename_longer_than_255_truncated():
    long_name = "a" * 300 + ".pdf"
    result = sanitize_filename(long_name)
    assert len(result) <= 255


@pytest.mark.unit
def test_filename_with_only_dots_returns_default():
    result = sanitize_filename("...")
    assert result == "resume.pdf"


# ── is_valid_email ─────────────────────────────────────────────────────────────


@pytest.mark.unit
def test_simple_email_valid():
    assert is_valid_email("user@example.com") is True


@pytest.mark.unit
def test_subdomain_email_valid():
    assert is_valid_email("user@mail.company.co.uk") is True


@pytest.mark.unit
def test_plus_addressing_valid():
    assert is_valid_email("user+tag@example.com") is True


@pytest.mark.unit
def test_missing_at_sign_invalid():
    assert is_valid_email("userexample.com") is False


@pytest.mark.unit
def test_missing_domain_invalid():
    assert is_valid_email("user@") is False


@pytest.mark.unit
def test_missing_tld_invalid():
    assert is_valid_email("user@example") is False


@pytest.mark.unit
def test_spaces_in_email_invalid():
    assert is_valid_email("user @example.com") is False


@pytest.mark.unit
def test_empty_string_invalid():
    assert is_valid_email("") is False


@pytest.mark.unit
def test_leading_whitespace_stripped_before_check():
    assert is_valid_email("  user@example.com  ") is True
