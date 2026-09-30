from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field

SupplierStatusValue = Literal["active", "inactive"]


class SupplierCreate(BaseModel):
    name: str = Field(min_length=2, max_length=160)
    document_number: str = Field(min_length=4, max_length=32)
    email: EmailStr | None = None
    category: str | None = Field(default=None, max_length=80)
    status: SupplierStatusValue = "active"


class SupplierUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=160)
    document_number: str | None = Field(default=None, min_length=4, max_length=32)
    email: EmailStr | None = None
    category: str | None = Field(default=None, max_length=80)
    status: SupplierStatusValue | None = None


class SupplierResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    company_id: UUID
    name: str
    document_number: str
    email: EmailStr | None
    category: str | None
    status: str
    created_at: datetime
    updated_at: datetime


class SupplierListResponse(BaseModel):
    items: list[SupplierResponse]
    total: int
    page: int
    page_size: int
