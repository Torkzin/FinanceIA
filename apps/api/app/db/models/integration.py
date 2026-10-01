from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import (
    JSON,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, CompanyOwnedMixin, TimestampMixin, UUIDPrimaryKeyMixin


class IntegrationConnection(UUIDPrimaryKeyMixin, CompanyOwnedMixin, TimestampMixin, Base):
    __tablename__ = "integration_connections"
    __table_args__ = (
        UniqueConstraint("company_id", "provider"),
        CheckConstraint("status IN ('active', 'inactive')", name="valid_status"),
    )

    provider: Mapped[str] = mapped_column(String(40), nullable=False)
    adapter: Mapped[str] = mapped_column(String(80), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="active", server_default="active")
    checkpoint: Mapped[str | None] = mapped_column(String(160))
    last_sync_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_sync_status: Mapped[str | None] = mapped_column(String(20))
    last_summary: Mapped[dict[str, Any] | None] = mapped_column(JSON)

    company: Mapped["Company"] = relationship(back_populates="integration_connections")  # noqa: F821
    sync_runs: Mapped[list["IntegrationSyncRun"]] = relationship(
        back_populates="connection", cascade="all, delete-orphan"
    )


class IntegrationSyncRun(UUIDPrimaryKeyMixin, CompanyOwnedMixin, Base):
    __tablename__ = "integration_sync_runs"
    __table_args__ = (
        CheckConstraint("status IN ('completed', 'failed')", name="valid_status"),
        Index("ix_integration_sync_runs_company_started", "company_id", "started_at"),
    )

    connection_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("integration_connections.id", ondelete="CASCADE"), nullable=False
    )
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    completed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    summary: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text)

    connection: Mapped[IntegrationConnection] = relationship(back_populates="sync_runs")
