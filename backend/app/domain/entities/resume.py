import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ResumeEntity(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    file_name: str
    file_path: str
    file_size: int
    mime_type: str
    parsed_text: str | None
    parsed_metadata: dict[str, object]
    is_active: bool
    created_at: datetime
    updated_at: datetime
