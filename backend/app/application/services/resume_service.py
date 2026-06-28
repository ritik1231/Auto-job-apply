"""Resume upload, retrieval, and deletion service."""

from __future__ import annotations

import uuid

import structlog

from app.core.config import settings
from app.core.sanitization import sanitize_filename
from app.domain.entities.resume import ResumeEntity
from app.domain.exceptions import (
    FileTooLargeError,
    InvalidFileTypeError,
    ResumeNotFoundError,
)
from app.domain.interfaces.repositories import IResumeRepository
from app.domain.interfaces.storage import IResumeStorage
from app.infrastructure.storage.pdf_parser import (
    build_parsed_metadata,
    extract_pdf_text,
    is_valid_pdf_bytes,
)

logger = structlog.get_logger(__name__)

PDF_MIME_TYPES = {"application/pdf", "application/x-pdf"}


class ResumeService:
    def __init__(
        self,
        resume_repo: IResumeRepository,
        storage: IResumeStorage,
    ) -> None:
        self._repo = resume_repo
        self._storage = storage

    async def upload_resume(
        self,
        user_id: uuid.UUID,
        file_content: bytes,
        original_filename: str,
        content_type: str,
        file_size: int,
    ) -> ResumeEntity:
        max_bytes = settings.RESUME_MAX_SIZE_MB * 1024 * 1024
        if file_size > max_bytes:
            raise FileTooLargeError(f"File exceeds {settings.RESUME_MAX_SIZE_MB}MB limit")

        # Validate by MIME type claim AND magic bytes (defence-in-depth)
        if content_type not in PDF_MIME_TYPES or not is_valid_pdf_bytes(file_content):
            raise InvalidFileTypeError("Only PDF files are accepted")

        safe_filename = sanitize_filename(original_filename)

        parsed_text = await extract_pdf_text(file_content)
        metadata = build_parsed_metadata(parsed_text, extraction_successful=bool(parsed_text))

        # One active resume per user
        await self._repo.deactivate_all_for_user(user_id)

        resume_id = uuid.uuid4()
        file_path = await self._storage.save(
            user_id=user_id,
            resume_id=resume_id,
            content=file_content,
            original_filename=safe_filename,
        )

        resume = await self._repo.create(
            id=resume_id,
            user_id=user_id,
            file_name=safe_filename,
            file_path=file_path,
            file_size=file_size,
            mime_type="application/pdf",
            parsed_text=parsed_text or None,
            parsed_metadata=metadata,
            is_active=True,
        )
        logger.info(
            "resume uploaded",
            user_id=str(user_id),
            resume_id=str(resume_id),
            char_count=metadata["char_count"],
        )
        return resume

    async def list_resumes(self, user_id: uuid.UUID) -> list[ResumeEntity]:
        return await self._repo.list_for_user(user_id)

    async def get_resume(self, user_id: uuid.UUID, resume_id: uuid.UUID) -> ResumeEntity:
        resume = await self._repo.get_by_id(resume_id)
        if resume is None or resume.user_id != user_id:
            raise ResumeNotFoundError("Resume not found")
        return resume

    async def delete_resume(self, user_id: uuid.UUID, resume_id: uuid.UUID) -> None:
        resume = await self._repo.get_by_id(resume_id)
        if resume is None or resume.user_id != user_id:
            raise ResumeNotFoundError("Resume not found")
        await self._repo.soft_delete(resume_id)
        logger.info("resume soft-deleted", resume_id=str(resume_id))
