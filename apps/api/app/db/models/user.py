from uuid import UUID

from sqlalchemy import Boolean, CheckConstraint, ForeignKey, String, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.db.models.enums import UserRole


class User(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "users"
    __table_args__ = (
        UniqueConstraint("company_id", "email"),
        CheckConstraint(
            "role IN ('admin', 'finance', 'manager')",
            name="valid_role",
        ),
    )

    company_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("companies.id", ondelete="CASCADE"), index=True
    )
    full_name: Mapped[str] = mapped_column(String(140), nullable=False)
    email: Mapped[str] = mapped_column(String(254), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(20), default=UserRole.FINANCE)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")

    company: Mapped["Company"] = relationship(back_populates="users")  # noqa: F821
    refresh_tokens: Mapped[list["RefreshToken"]] = relationship(  # noqa: F821
        back_populates="user", cascade="all, delete-orphan"
    )
