from datetime import date
from decimal import Decimal
from uuid import UUID

from sqlalchemy import (
    CheckConstraint,
    Date,
    ForeignKey,
    Index,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, CompanyOwnedMixin, TimestampMixin, UUIDPrimaryKeyMixin
from app.db.models.enums import InvoiceSource, InvoiceStatus


class Invoice(UUIDPrimaryKeyMixin, CompanyOwnedMixin, TimestampMixin, Base):
    __tablename__ = "invoices"
    __table_args__ = (
        UniqueConstraint("company_id", "supplier_id", "invoice_number"),
        CheckConstraint("amount > 0", name="positive_amount"),
        CheckConstraint("due_date >= issue_date", name="valid_date_range"),
        CheckConstraint("char_length(currency) = 3", name="valid_currency"),
        CheckConstraint(
            "status IN ('pending', 'approved', 'paid', 'overdue', 'rejected')",
            name="valid_status",
        ),
        CheckConstraint("source IN ('manual', 'document', 'erp')", name="valid_source"),
        CheckConstraint(
            "ai_confidence IS NULL OR (ai_confidence >= 0 AND ai_confidence <= 1)",
            name="valid_ai_confidence",
        ),
        Index("ix_invoices_company_status_due_date", "company_id", "status", "due_date"),
        Index("ix_invoices_company_issue_date", "company_id", "issue_date"),
    )

    supplier_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("suppliers.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    cost_center_id: Mapped[UUID | None] = mapped_column(
        Uuid, ForeignKey("cost_centers.id", ondelete="SET NULL"), index=True
    )
    invoice_number: Mapped[str] = mapped_column(String(80), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    issue_date: Mapped[date] = mapped_column(Date, nullable=False)
    due_date: Mapped[date] = mapped_column(Date, nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="BRL", server_default="BRL")
    status: Mapped[str] = mapped_column(String(20), default=InvoiceStatus.PENDING)
    source: Mapped[str] = mapped_column(String(20), default=InvoiceSource.MANUAL)
    ai_confidence: Mapped[Decimal | None] = mapped_column(Numeric(5, 4))

    company: Mapped["Company"] = relationship(back_populates="invoices")  # noqa: F821
    supplier: Mapped["Supplier"] = relationship(back_populates="invoices")  # noqa: F821
    cost_center: Mapped["CostCenter | None"] = relationship(back_populates="invoices")  # noqa: F821
