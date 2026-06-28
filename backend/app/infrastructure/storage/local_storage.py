"""Local filesystem implementation of IResumeStorage."""

from __future__ import annotations

import asyncio
import uuid
from pathlib import Path

import structlog

from app.core.config import settings
from app.domain.exceptions import StorageError
from app.domain.interfaces.storage import IResumeStorage

logger = structlog.get_logger(__name__)


class LocalResumeStorage(IResumeStorage):
    def __init__(self, base_path: str | None = None) -> None:
        self._base = Path(base_path or settings.RESUME_STORAGE_PATH)

    def _resume_path(self, user_id: uuid.UUID, resume_id: uuid.UUID) -> Path:
        return self._base / str(user_id) / f"{resume_id}.pdf"

    async def save(
        self,
        user_id: uuid.UUID,
        resume_id: uuid.UUID,
        content: bytes,
        original_filename: str,  # kept for interface compat; not used in path
    ) -> str:
        path = self._resume_path(user_id, resume_id)
        try:
            await asyncio.to_thread(path.parent.mkdir, parents=True, exist_ok=True)
            await asyncio.to_thread(path.write_bytes, content)
        except OSError as exc:
            logger.error("resume save failed", path=str(path), error=str(exc))
            raise StorageError(f"Failed to save resume: {exc}") from exc
        logger.info("resume saved", path=str(path), size=len(content))
        return str(path)

    async def get(self, file_path: str) -> bytes:
        path = Path(file_path)
        try:
            return await asyncio.to_thread(path.read_bytes)
        except OSError as exc:
            raise StorageError(f"Failed to read resume: {exc}") from exc

    async def delete(self, file_path: str) -> None:
        path = Path(file_path)
        try:
            await asyncio.to_thread(path.unlink, True)  # missing_ok=True
        except OSError as exc:
            logger.warning("resume delete failed", path=str(path), error=str(exc))
