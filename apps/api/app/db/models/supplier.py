from sqlalchemy import CheckConstraint, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, CompanyOwnedMixin, TimestampMixin, UUIDPrimaryKeyMixin
from app.db.models.enums import SupplierStatus


class Supplier(UUIDPrimaryKeyMixin, CompanyOwnedMixin, TimestampMixin, Base):
    __tablename__ = "suppliers"
    __table_args__ = (
        UniqueConstraint("company_id", "document_number"),
        CheckConstraint("status IN ('active', 'inactive')", name="valid_status"),
    )

    name: Mapped[str] = mapped_column(String(160), nullable=False)
    document_number: Mapped[str] = mapped_column(String(32), nullable=False)
    email: Mapped[str | None] = mapped_column(String(254))
    category: Mapped[str | None] = mapped_column(String(80))
    status: Mapped[str] = mapped_column(String(20), default=SupplierStatus.ACTIVE)

    company: Mapped["Company"] = relationship(back_populates="suppliers")  # noqa: F821
    invoices: Mapped[list["Invoice"]] = relationship(back_populates="supplier")  # noqa: F821
