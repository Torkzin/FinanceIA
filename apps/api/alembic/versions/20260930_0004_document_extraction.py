"""Add human-reviewed AI extraction fields.

Revision ID: 20260930_0004
Revises: 20260930_0003
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "20260930_0004"
down_revision: str | None = "20260930_0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("financial_documents", sa.Column("extraction_data", postgresql.JSONB()))
    op.add_column("financial_documents", sa.Column("extraction_provider", sa.String(40)))
    op.add_column("financial_documents", sa.Column("extraction_model", sa.String(100)))
    op.add_column("financial_documents", sa.Column("extraction_error", sa.String(500)))
    op.add_column("financial_documents", sa.Column("extracted_at", sa.DateTime(timezone=True)))
    op.add_column("financial_documents", sa.Column("confirmed_invoice_id", sa.Uuid()))
    op.create_unique_constraint(
        "uq_financial_documents_confirmed_invoice_id",
        "financial_documents",
        ["confirmed_invoice_id"],
    )
    op.create_foreign_key(
        "fk_financial_documents_confirmed_invoice_id_invoices",
        "financial_documents",
        "invoices",
        ["confirmed_invoice_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_financial_documents_confirmed_invoice_id_invoices",
        "financial_documents",
        type_="foreignkey",
    )
    op.drop_constraint(
        "uq_financial_documents_confirmed_invoice_id",
        "financial_documents",
        type_="unique",
    )
    op.drop_column("financial_documents", "confirmed_invoice_id")
    op.drop_column("financial_documents", "extracted_at")
    op.drop_column("financial_documents", "extraction_error")
    op.drop_column("financial_documents", "extraction_model")
    op.drop_column("financial_documents", "extraction_provider")
    op.drop_column("financial_documents", "extraction_data")
