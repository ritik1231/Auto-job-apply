import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class UserEntity(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    google_id: str
    email: str
    name: str | None
    picture_url: str | None
    # Gmail tokens are intentionally excluded — never leave the backend.
    gmail_token_expiry: datetime | None
    current_ctc: str | None = None
    expected_ctc: str | None = None
    notice_period: str | None = None
    current_location: str | None = None
    total_experience: str | None = None
    linkedin_url: str | None = None
    daily_quota_override: int | None = None
    is_active: bool
    created_at: datetime
    updated_at: datetime
