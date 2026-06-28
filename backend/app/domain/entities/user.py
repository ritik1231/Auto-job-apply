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
    is_active: bool
    created_at: datetime
    updated_at: datetime
