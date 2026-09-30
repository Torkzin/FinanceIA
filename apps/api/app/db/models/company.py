from sqlalchemy import Boolean, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class Company(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "companies"

    name: Mapped[str] = mapped_column(String(160), nullable=False)
    slug: Mapped[str] = mapped_column(String(80), unique=True, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")

    users: Mapped[list["User"]] = relationship(back_populates="company")  # noqa: F821
    suppliers: Mapped[list["Supplier"]] = relationship(back_populates="company")  # noqa: F821
    cost_centers: Mapped[list["CostCenter"]] = relationship(back_populates="company")  # noqa: F821
    invoices: Mapped[list["Invoice"]] = relationship(back_populates="company")  # noqa: F821
