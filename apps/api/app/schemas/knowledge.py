from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class KnowledgeDocumentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    original_name: str
    media_type: str
    size_bytes: int
    status: str
    uploaded_at: datetime
    indexed_at: datetime | None
    page_count: int | None
    chunk_count: int
    embedding_provider: str | None
    embedding_model: str | None
    processing_error: str | None


class KnowledgeDocumentListResponse(BaseModel):
    items: list[KnowledgeDocumentResponse]
    total: int


class KnowledgeQueryRequest(BaseModel):
    question: str = Field(min_length=3, max_length=1000)
    limit: int = Field(default=5, ge=1, le=8)


class KnowledgeSource(BaseModel):
    document_id: UUID
    document_name: str
    excerpt: str
    page_number: int | None
    similarity: float = Field(ge=0, le=1)


class KnowledgeQueryResponse(BaseModel):
    answer: str
    sources: list[KnowledgeSource]
    grounded: bool
    provider: str
    model: str
