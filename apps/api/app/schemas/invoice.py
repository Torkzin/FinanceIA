from datetime import date, datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

InvoiceStatusValue = Literal["pending", "approved", "paid", "overdue", "rejected"]
InvoiceSourceValue = Literal["manual", "document", "erp"]


class InvoiceBase(BaseModel):
    supplier_id: UUID
    cost_center_id: UUID | None = None
    invoice_number: str = Field(min_length=1, max_length=80)
    description: str = Field(min_length=2, max_length=2000)
    category: str = Field(min_length=2, max_length=80)
    issue_date: date
    due_date: date
    amount: Decimal = Field(gt=0, max_digits=14, decimal_places=2)
    currency: str = Field(default="BRL", min_length=3, max_length=3)
    status: InvoiceStatusValue = "pending"
    source: InvoiceSourceValue = "manual"

    @field_validator("currency")
    @classmethod
    def normalize_currency(cls, value: str) -> str:
        return value.upper()

    @field_validator("due_date")
    @classmethod
    def validate_due_date(cls, value: date, info) -> date:
        issue_date = info.data.get("issue_date")
        if issue_date and value < issue_date:
            raise ValueError("due_date must be on or after issue_date")
        return value


class InvoiceCreate(InvoiceBase):
    pass


class InvoiceUpdate(BaseModel):
    supplier_id: UUID | None = None
    cost_center_id: UUID | None = None
    invoice_number: str | None = Field(default=None, min_length=1, max_length=80)
    description: str | None = Field(default=None, min_length=2, max_length=2000)
    category: str | None = Field(default=None, min_length=2, max_length=80)
    issue_date: date | None = None
    due_date: date | None = None
    amount: Decimal | None = Field(default=None, gt=0, max_digits=14, decimal_places=2)
    currency: str | None = Field(default=None, min_length=3, max_length=3)
    status: InvoiceStatusValue | None = None
    source: InvoiceSourceValue | None = None

    @field_validator("currency")
    @classmethod
    def normalize_currency(cls, value: str | None) -> str | None:
        return value.upper() if value else value


class InvoiceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    company_id: UUID
    supplier_id: UUID
    cost_center_id: UUID | None
    invoice_number: str
    description: str
    category: str
    issue_date: date
    due_date: date
    amount: Decimal
    currency: str
    status: str
    source: str
    ai_confidence: Decimal | None
    created_at: datetime
    updated_at: datetime


class InvoiceListResponse(BaseModel):
    items: list[InvoiceResponse]
    total: int
    page: int
    page_size: int
