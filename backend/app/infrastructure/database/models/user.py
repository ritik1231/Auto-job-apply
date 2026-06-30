from datetime import datetime

import sqlalchemy as sa
from sqlalchemy import Boolean, DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.infrastructure.database.base import TimestampedBase


class User(TimestampedBase):
    __tablename__ = "users"

    google_id: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    name: Mapped[str | None] = mapped_column(String(255))
    picture_url: Mapped[str | None] = mapped_column(Text)

    # Stored encrypted (AES-256); never returned to the extension directly.
    gmail_access_token: Mapped[str | None] = mapped_column(Text)
    gmail_refresh_token: Mapped[str | None] = mapped_column(Text)
    gmail_token_expiry: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    current_ctc: Mapped[str | None] = mapped_column(String(100))
    expected_ctc: Mapped[str | None] = mapped_column(String(100))
    notice_period: Mapped[str | None] = mapped_column(String(100))
    current_location: Mapped[str | None] = mapped_column(String(255))
    total_experience: Mapped[str | None] = mapped_column(String(100))
    linkedin_url: Mapped[str | None] = mapped_column(String(500))
    github_url: Mapped[str | None] = mapped_column(String(500))
    website_url: Mapped[str | None] = mapped_column(String(500))
    daily_quota_override: Mapped[int | None] = mapped_column(sa.Integer(), nullable=True)

    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="true"
    )

    resumes: Mapped[list["Resume"]] = relationship(  # type: ignore[name-defined]  # noqa: F821
        back_populates="user", cascade="all, delete-orphan", lazy="noload"
    )
    job_posts: Mapped[list["JobPost"]] = relationship(  # type: ignore[name-defined]  # noqa: F821
        back_populates="user", cascade="all, delete-orphan", lazy="noload"
    )
    applications: Mapped[list["Application"]] = relationship(  # type: ignore[name-defined]  # noqa: F821
        back_populates="user", cascade="all, delete-orphan", lazy="noload"
    )

    def __repr__(self) -> str:
        return f"<User id={self.id} email={self.email!r}>"
