from datetime import date, datetime
from decimal import Decimal
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, model_validator


class ERPVendor(BaseModel):
    external_id: str = Field(min_length=1, max_length=80)
    name: str = Field(min_length=2, max_length=160)
    document_number: str = Field(min_length=4, max_length=32)
    email: EmailStr | None = None
    category: str | None = Field(default=None, max_length=80)
    status: Literal["active", "inactive"] = "active"


class ERPInvoice(BaseModel):
    external_id: str = Field(min_length=1, max_length=80)
    vendor_external_id: str = Field(min_length=1, max_length=80)
    cost_center_code: str | None = Field(default=None, max_length=30)
    invoice_number: str = Field(min_length=1, max_length=80)
    description: str = Field(min_length=2, max_length=2000)
    category: str = Field(min_length=2, max_length=80)
    issue_date: date
    due_date: date
    amount: Decimal = Field(gt=0, max_digits=14, decimal_places=2)
    currency: str = Field(default="BRL", min_length=3, max_length=3)
    status: Literal["pending", "approved", "paid", "overdue", "rejected"] = "pending"

    @model_validator(mode="after")
    def validate_dates(self) -> "ERPInvoice":
        if self.due_date < self.issue_date:
            raise ValueError("due_date must be on or after issue_date")
        self.currency = self.currency.upper()
        return self


class ERPSnapshot(BaseModel):
    source: str
    generated_at: datetime
    vendors: list[ERPVendor]
    invoices: list[ERPInvoice]


class ERPSyncCounts(BaseModel):
    received: int = 0
    created: int = 0
    updated: int = 0
    skipped: int = 0


class ERPConnectionState(BaseModel):
    adapter: str
    status: str
    checkpoint: str | None = None
    last_sync_at: datetime | None = None
    last_sync_status: str | None = None


class ERPPreviewResponse(BaseModel):
    source: str
    generated_at: datetime
    vendor_count: int
    invoice_count: int
    connection: ERPConnectionState | None = None


class ERPSyncResponse(BaseModel):
    run_id: UUID
    source: str
    checkpoint: str
    vendors: ERPSyncCounts
    invoices: ERPSyncCounts
    warnings: list[str]
    completed_at: datetime


class ERPSyncRunResponse(BaseModel):
    id: UUID
    status: str
    started_at: datetime
    completed_at: datetime
    summary: dict[str, Any]
    error_message: str | None


class ERPSyncRunListResponse(BaseModel):
    items: list[ERPSyncRunResponse]
    total: int
