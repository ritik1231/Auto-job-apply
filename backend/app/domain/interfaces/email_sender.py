"""Email sender interface — implemented by the Gmail client in infrastructure."""

from abc import ABC, abstractmethod


class IEmailSender(ABC):
    @abstractmethod
    async def send(
        self,
        to_address: str,
        subject: str,
        body: str,
        attachment_content: bytes | None = None,
        attachment_filename: str | None = None,
        attachment_mime_type: str = "application/pdf",
    ) -> str:
        """Send an email and return the provider message ID."""
        ...
