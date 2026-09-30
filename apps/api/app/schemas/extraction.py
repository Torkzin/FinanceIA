from datetime import date, datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, model_validator


class ExtractedInvoiceData(BaseModel):
    document_type: str | None = Field(
        description="Type such as invoice, boleto, receipt, or unknown"
    )
    supplier_name: str | None
    supplier_document_number: str | None
    invoice_number: str | None
    amount: float | None = Field(default=None, ge=0)
    currency: str | None
    issue_date: date | None
    due_date: date | None
    description: str | None
    category: str | None
    cost_center_name: str | None
    confidence: float = Field(ge=0, le=1)
    warnings: list[str]


class DocumentExtractionResponse(BaseModel):
    document_id: UUID
    status: str
    provider: str | None
    model: str | None
    data: ExtractedInvoiceData | None
    suggested_supplier_id: UUID | None = None
    suggested_cost_center_id: UUID | None = None
    confirmed_invoice_id: UUID | None = None
    extracted_at: datetime | None = None
    error: str | None = None


class ConfirmDocumentExtraction(BaseModel):
    supplier_id: UUID
    cost_center_id: UUID | None = None
    invoice_number: str = Field(min_length=1, max_length=80)
    description: str = Field(min_length=2, max_length=2000)
    category: str = Field(min_length=2, max_length=80)
    issue_date: date
    due_date: date
    amount: Decimal = Field(gt=0, max_digits=14, decimal_places=2)
    currency: str = Field(default="BRL", min_length=3, max_length=3)
    status: Literal["pending", "approved"] = "pending"

    @model_validator(mode="after")
    def validate_dates_and_currency(self) -> "ConfirmDocumentExtraction":
        if self.due_date < self.issue_date:
            raise ValueError("due_date must be on or after issue_date")
        self.currency = self.currency.upper()
        return self
