from sqlalchemy import String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, CompanyOwnedMixin, UUIDPrimaryKeyMixin


class CostCenter(UUIDPrimaryKeyMixin, CompanyOwnedMixin, Base):
    __tablename__ = "cost_centers"
    __table_args__ = (UniqueConstraint("company_id", "code"),)

    name: Mapped[str] = mapped_column(String(120), nullable=False)
    code: Mapped[str] = mapped_column(String(30), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)

    company: Mapped["Company"] = relationship(back_populates="cost_centers")  # noqa: F821
    invoices: Mapped[list["Invoice"]] = relationship(back_populates="cost_center")  # noqa: F821
