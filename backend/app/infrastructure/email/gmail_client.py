"""Gmail implementation of IEmailSender using the Google API Python Client."""

from __future__ import annotations

import asyncio
import base64
from datetime import UTC, datetime, timedelta
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import structlog
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from app.core.config import settings
from app.core.security import decrypt_token, encrypt_token
from app.domain.exceptions import GmailSendError, OAuthError
from app.domain.interfaces.email_sender import IEmailSender

logger = structlog.get_logger(__name__)

_REFRESH_BUFFER = timedelta(seconds=60)
_TOKEN_URI = "https://oauth2.googleapis.com/token"


class GmailEmailSender(IEmailSender):
    """Sends email via the Gmail REST API using a user's stored OAuth credentials.

    Instantiated per-request. After send(), inspect `tokens_refreshed`,
    `new_access_token_enc`, and `new_expiry` to persist any token refresh.
    """

    def __init__(
        self,
        access_token_enc: str | None,
        refresh_token_enc: str | None,
        expiry: datetime | None,
    ) -> None:
        self._access_enc = access_token_enc
        self._refresh_enc = refresh_token_enc
        self._expiry = expiry

        self.tokens_refreshed: bool = False
        self.new_access_token_enc: str | None = None
        self.new_expiry: datetime | None = None

    async def send(
        self,
        to_address: str,
        subject: str,
        body: str,
        attachment_content: bytes | None = None,
        attachment_filename: str | None = None,
        attachment_mime_type: str = "application/pdf",
    ) -> str:
        """Build, send, and return the Gmail message ID."""
        creds = self._build_credentials()

        if self._needs_refresh(creds):
            await self._refresh_credentials(creds)

        message = _build_mime_message(
            to_address=to_address,
            subject=subject,
            body=body,
            attachment_content=attachment_content,
            attachment_filename=attachment_filename,
            attachment_mime_type=attachment_mime_type,
        )
        raw = base64.urlsafe_b64encode(message.as_bytes()).decode()

        try:
            service = build("gmail", "v1", credentials=creds)
            result = await asyncio.to_thread(
                service.users().messages().send(userId="me", body={"raw": raw}).execute
            )
        except HttpError as exc:
            status = exc.resp.status if exc.resp else "unknown"
            logger.error("gmail api http error", status=status, error=str(exc))
            raise GmailSendError(f"Gmail API returned {status}: {exc.reason}") from exc
        except Exception as exc:
            logger.error("unexpected gmail send error", error=str(exc))
            raise GmailSendError(f"Failed to send email via Gmail: {exc}") from exc

        message_id: str = result["id"]
        logger.info("email sent via gmail", gmail_message_id=message_id, to=to_address)
        return message_id

    # ── private ────────────────────────────────────────────────────────────────

    def _build_credentials(self):
        from google.oauth2.credentials import Credentials

        access = decrypt_token(self._access_enc) if self._access_enc else None
        refresh = decrypt_token(self._refresh_enc) if self._refresh_enc else None
        # google-auth compares expiry using datetime.utcnow() (naive),
        # so Credentials must receive a naive UTC datetime.
        expiry = self._expiry
        if expiry is not None and expiry.tzinfo is not None:
            expiry = expiry.replace(tzinfo=None)
        return Credentials(
            token=access,
            refresh_token=refresh,
            token_uri=_TOKEN_URI,
            client_id=settings.GOOGLE_CLIENT_ID,
            client_secret=settings.GOOGLE_CLIENT_SECRET,
            expiry=expiry,
        )

    @staticmethod
    def _needs_refresh(creds) -> bool:
        if not creds.token:
            return True
        if creds.expiry is None:
            return False
        expiry = creds.expiry
        if expiry.tzinfo is None:
            expiry = expiry.replace(tzinfo=UTC)
        return datetime.now(tz=UTC) >= (expiry - _REFRESH_BUFFER)

    async def _refresh_credentials(self, creds) -> None:
        if not creds.refresh_token:
            raise OAuthError(
                "No Gmail refresh token available — please sign in again to grant access"
            )
        try:
            from google.auth.transport.requests import Request

            await asyncio.to_thread(creds.refresh, Request())
        except Exception as exc:
            logger.warning("gmail token refresh failed", error=str(exc))
            raise OAuthError(f"Gmail token refresh failed: {exc}") from exc

        self.tokens_refreshed = True
        self.new_access_token_enc = encrypt_token(creds.token)
        new_expiry = creds.expiry
        if new_expiry and new_expiry.tzinfo is None:
            new_expiry = new_expiry.replace(tzinfo=UTC)
        self.new_expiry = new_expiry
        logger.info("gmail access token refreshed and encrypted")


def _build_mime_message(
    *,
    to_address: str,
    subject: str,
    body: str,
    attachment_content: bytes | None,
    attachment_filename: str | None,
    attachment_mime_type: str,
):
    msg: MIMEMultipart | MIMEText
    if attachment_content and attachment_filename:
        msg = MIMEMultipart()
        msg.attach(MIMEText(body, "plain", "utf-8"))
        subtype = attachment_mime_type.split("/", 1)[-1]
        part = MIMEApplication(attachment_content, _subtype=subtype)
        part.add_header("Content-Disposition", "attachment", filename=attachment_filename)
        msg.attach(part)
    else:
        msg = MIMEText(body, "plain", "utf-8")

    msg["to"] = to_address
    msg["subject"] = subject
    return msg
