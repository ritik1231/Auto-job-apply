"""Resume file storage interface."""

import uuid
from abc import ABC, abstractmethod


class IResumeStorage(ABC):
    @abstractmethod
    async def save(
        self,
        user_id: uuid.UUID,
        resume_id: uuid.UUID,
        content: bytes,
        original_filename: str,
    ) -> str:
        """Persist the PDF bytes and return the storage path."""
        ...

    @abstractmethod
    async def get(self, file_path: str) -> bytes:
        """Return the raw bytes for a stored resume."""
        ...

    @abstractmethod
    async def delete(self, file_path: str) -> None:
        """Remove a stored resume. Silently succeeds if already absent."""
        ...
