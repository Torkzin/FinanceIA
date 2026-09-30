from datetime import datetime
from uuid import UUID

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKey,
    String,
    UniqueConstraint,
    Uuid,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, CompanyOwnedMixin, TimestampMixin, UUIDPrimaryKeyMixin


class FinancialDocument(UUIDPrimaryKeyMixin, CompanyOwnedMixin, TimestampMixin, Base):
    __tablename__ = "financial_documents"
    __table_args__ = (
        UniqueConstraint("company_id", "sha256"),
        CheckConstraint("size_bytes > 0", name="positive_size"),
        CheckConstraint(
            "status IN ('uploaded', 'processing', 'review', 'completed', 'failed')",
            name="valid_status",
        ),
    )

    original_name: Mapped[str] = mapped_column(String(255), nullable=False)
    storage_key: Mapped[str] = mapped_column(String(500), unique=True, nullable=False)
    media_type: Mapped[str] = mapped_column(String(100), nullable=False)
    size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(20), default="uploaded", server_default="uploaded")
    uploaded_by_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    uploaded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    extraction_data: Mapped[dict | None] = mapped_column(JSONB)
    extraction_provider: Mapped[str | None] = mapped_column(String(40))
    extraction_model: Mapped[str | None] = mapped_column(String(100))
    extraction_error: Mapped[str | None] = mapped_column(String(500))
    extracted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    confirmed_invoice_id: Mapped[UUID | None] = mapped_column(
        Uuid, ForeignKey("invoices.id", ondelete="SET NULL"), unique=True
    )

    company: Mapped["Company"] = relationship()  # noqa: F821
    uploaded_by: Mapped["User"] = relationship()  # noqa: F821
    confirmed_invoice: Mapped["Invoice | None"] = relationship()  # noqa: F821
