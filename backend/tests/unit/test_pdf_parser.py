"""Unit tests for the PDF parser and validation utilities."""

from __future__ import annotations

import pytest

from app.infrastructure.storage.pdf_parser import (
    build_parsed_metadata,
    extract_pdf_text,
    is_valid_pdf_bytes,
)

# ── Minimal PDF factory ────────────────────────────────────────────────────────


def _make_minimal_pdf(text: str = "Hello PDF") -> bytes:
    """Build a syntactically valid PDF-1.4 document containing a single text line."""
    content = f"BT /F1 12 Tf 72 720 Td ({text}) Tj ET".encode()

    obj1 = b"1 0 obj\n<</Type/Catalog/Pages 2 0 R>>\nendobj\n"
    obj2 = b"2 0 obj\n<</Type/Pages/Kids[3 0 R]/Count 1>>\nendobj\n"
    obj3 = (
        b"3 0 obj\n<</Type/Page/Parent 2 0 R/MediaBox[0 0 612 792]"
        b"/Contents 4 0 R/Resources<</Font<</F1 5 0 R>>>>>>\nendobj\n"
    )
    obj4 = (
        b"4 0 obj\n<</Length "
        + str(len(content)).encode()
        + b">>\nstream\n"
        + content
        + b"\nendstream\nendobj\n"
    )
    obj5 = b"5 0 obj\n<</Type/Font/Subtype/Type1/BaseFont/Helvetica>>\nendobj\n"

    header = b"%PDF-1.4\n"
    objects = [obj1, obj2, obj3, obj4, obj5]

    body = b""
    offsets: list[int] = []
    for obj in objects:
        offsets.append(len(header) + len(body))
        body += obj

    xref_pos = len(header) + len(body)
    xref = b"xref\n0 6\n0000000000 65535 f \n"
    for off in offsets:
        xref += f"{off:010d} 00000 n \n".encode()

    trailer = (f"trailer\n<</Size 6/Root 1 0 R>>\nstartxref\n{xref_pos}\n%%EOF\n").encode()

    return header + body + xref + trailer


# ── Magic-byte validation ──────────────────────────────────────────────────────


@pytest.mark.unit
def test_pdf_magic_bytes_accepted():
    assert is_valid_pdf_bytes(b"%PDF-1.4 rest of file")


@pytest.mark.unit
def test_non_pdf_magic_bytes_rejected():
    assert not is_valid_pdf_bytes(b"PK\x03\x04")  # zip / docx


@pytest.mark.unit
def test_empty_bytes_rejected():
    assert not is_valid_pdf_bytes(b"")


@pytest.mark.unit
def test_short_bytes_rejected():
    assert not is_valid_pdf_bytes(b"%PDF")  # 4 bytes, need 5


# ── Text extraction ────────────────────────────────────────────────────────────


@pytest.mark.asyncio
@pytest.mark.unit
async def test_extract_pdf_text_returns_string_for_valid_pdf():
    pdf = _make_minimal_pdf("Resume test content")
    result = await extract_pdf_text(pdf)
    assert isinstance(result, str)


@pytest.mark.asyncio
@pytest.mark.unit
async def test_extract_pdf_text_graceful_on_invalid_bytes():
    result = await extract_pdf_text(b"not a pdf at all")
    assert result == ""


@pytest.mark.asyncio
@pytest.mark.unit
async def test_extract_pdf_text_graceful_on_empty_bytes():
    result = await extract_pdf_text(b"")
    assert result == ""


# ── Metadata builder ───────────────────────────────────────────────────────────


@pytest.mark.unit
def test_build_parsed_metadata_with_text():
    meta = build_parsed_metadata("hello world", extraction_successful=True)
    assert meta["char_count"] == 11
    assert meta["extraction_successful"] is True


@pytest.mark.unit
def test_build_parsed_metadata_empty():
    meta = build_parsed_metadata("", extraction_successful=False)
    assert meta["char_count"] == 0
    assert meta["extraction_successful"] is False
