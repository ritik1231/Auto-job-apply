"""PDF text extraction using pdfminer.six."""

from __future__ import annotations

import asyncio
from io import BytesIO

import structlog
from pdfminer.high_level import extract_text
from pdfminer.pdftypes import PDFException

logger = structlog.get_logger(__name__)

PDF_MAGIC = b"%PDF-"


def is_valid_pdf_bytes(content: bytes) -> bool:
    """Return True if the first bytes match the PDF magic signature."""
    return content[:5] == PDF_MAGIC


def _extract_text_sync(content: bytes) -> str:
    """Blocking PDF text extraction — run in a thread via extract_pdf_text()."""
    return extract_text(BytesIO(content))


async def extract_pdf_text(content: bytes) -> str:
    """Extract all text from PDF bytes. Returns empty string on parse failure."""
    try:
        text = await asyncio.to_thread(_extract_text_sync, content)
        return text.strip()
    except (PDFException, Exception) as exc:
        logger.warning("pdf text extraction failed", error=str(exc))
        return ""


def build_parsed_metadata(text: str, extraction_successful: bool) -> dict[str, object]:
    return {
        "char_count": len(text),
        "extraction_successful": extraction_successful,
    }
