"""Supabase S3-compatible storage backend for resume files."""

from __future__ import annotations

import asyncio
import uuid
from functools import cached_property

import structlog

from app.core.config import settings
from app.domain.exceptions import StorageError
from app.domain.interfaces.storage import IResumeStorage

logger = structlog.get_logger(__name__)


class SupabaseResumeStorage(IResumeStorage):
    def _object_key(self, user_id: uuid.UUID, resume_id: uuid.UUID) -> str:
        return f"{user_id}/{resume_id}.pdf"

    @cached_property
    def _client(self):
        import boto3

        return boto3.client(
            "s3",
            endpoint_url=settings.SUPABASE_S3_ENDPOINT,
            aws_access_key_id=settings.SUPABASE_S3_ACCESS_KEY,
            aws_secret_access_key=settings.SUPABASE_S3_SECRET_KEY,
            region_name=settings.SUPABASE_S3_REGION,
        )

    async def save(
        self,
        user_id: uuid.UUID,
        resume_id: uuid.UUID,
        content: bytes,
        original_filename: str,
    ) -> str:
        key = self._object_key(user_id, resume_id)
        try:
            await asyncio.to_thread(
                self._client.put_object,
                Bucket=settings.SUPABASE_BUCKET_NAME,
                Key=key,
                Body=content,
                ContentType="application/pdf",
            )
        except Exception as exc:
            logger.error("supabase upload failed", key=key, error=str(exc))
            raise StorageError(f"Failed to upload resume: {exc}") from exc
        logger.info("resume uploaded to supabase", key=key, size=len(content))
        return key

    async def get(self, file_path: str) -> bytes:
        try:
            response = await asyncio.to_thread(
                self._client.get_object,
                Bucket=settings.SUPABASE_BUCKET_NAME,
                Key=file_path,
            )
            return await asyncio.to_thread(response["Body"].read)
        except Exception as exc:
            logger.error("supabase download failed", key=file_path, error=str(exc))
            raise StorageError(f"Failed to download resume: {exc}") from exc

    async def delete(self, file_path: str) -> None:
        try:
            await asyncio.to_thread(
                self._client.delete_object,
                Bucket=settings.SUPABASE_BUCKET_NAME,
                Key=file_path,
            )
        except Exception as exc:
            logger.warning("supabase delete failed", key=file_path, error=str(exc))
