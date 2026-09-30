from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class DocumentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    company_id: UUID
    original_name: str
    media_type: str
    size_bytes: int
    sha256: str
    status: str
    uploaded_by_id: UUID
    uploaded_at: datetime


class DocumentListResponse(BaseModel):
    items: list[DocumentResponse]
    total: int
