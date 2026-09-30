"""Add secure financial document metadata.

Revision ID: 20260930_0003
Revises: 20260930_0002
Create Date: 2026-09-30
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260930_0003"
down_revision: str | None = "20260930_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "financial_documents",
        sa.Column("original_name", sa.String(length=255), nullable=False),
        sa.Column("storage_key", sa.String(length=500), nullable=False),
        sa.Column("media_type", sa.String(length=100), nullable=False),
        sa.Column("size_bytes", sa.BigInteger(), nullable=False),
        sa.Column("sha256", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=20), server_default="uploaded", nullable=False),
        sa.Column("uploaded_by_id", sa.Uuid(), nullable=False),
        sa.Column(
            "uploaded_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("company_id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint("size_bytes > 0", name=op.f("ck_financial_documents_positive_size")),
        sa.CheckConstraint(
            "status IN ('uploaded', 'processing', 'review', 'completed', 'failed')",
            name=op.f("ck_financial_documents_valid_status"),
        ),
        sa.ForeignKeyConstraint(
            ["company_id"],
            ["companies.id"],
            name=op.f("fk_financial_documents_company_id_companies"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["uploaded_by_id"],
            ["users.id"],
            name=op.f("fk_financial_documents_uploaded_by_id_users"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_financial_documents")),
        sa.UniqueConstraint(
            "company_id", "sha256", name=op.f("uq_financial_documents_company_id_sha256")
        ),
        sa.UniqueConstraint("storage_key", name=op.f("uq_financial_documents_storage_key")),
    )
    op.create_index(
        op.f("ix_financial_documents_company_id"),
        "financial_documents",
        ["company_id"],
    )
    op.create_index(op.f("ix_financial_documents_sha256"), "financial_documents", ["sha256"])
    op.create_index(
        op.f("ix_financial_documents_uploaded_by_id"),
        "financial_documents",
        ["uploaded_by_id"],
    )


def downgrade() -> None:
    op.drop_table("financial_documents")
