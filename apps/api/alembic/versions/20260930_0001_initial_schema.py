"""Create the initial multi-tenant financial schema.

Revision ID: 20260930_0001
Revises:
Create Date: 2026-09-30
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260930_0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    op.create_table(
        "companies",
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("slug", sa.String(length=80), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_companies")),
        sa.UniqueConstraint("slug", name=op.f("uq_companies_slug")),
    )
    op.create_table(
        "cost_centers",
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("code", sa.String(length=30), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("company_id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(
            ["company_id"],
            ["companies.id"],
            name=op.f("fk_cost_centers_company_id_companies"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_cost_centers")),
        sa.UniqueConstraint("company_id", "code", name=op.f("uq_cost_centers_company_id_code")),
    )
    op.create_index(op.f("ix_cost_centers_company_id"), "cost_centers", ["company_id"])
    op.create_table(
        "suppliers",
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("document_number", sa.String(length=32), nullable=False),
        sa.Column("email", sa.String(length=254), nullable=True),
        sa.Column("category", sa.String(length=80), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("company_id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint(
            "status IN ('active', 'inactive')", name=op.f("ck_suppliers_valid_status")
        ),
        sa.ForeignKeyConstraint(
            ["company_id"],
            ["companies.id"],
            name=op.f("fk_suppliers_company_id_companies"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_suppliers")),
        sa.UniqueConstraint(
            "company_id", "document_number", name=op.f("uq_suppliers_company_id_document_number")
        ),
    )
    op.create_index(op.f("ix_suppliers_company_id"), "suppliers", ["company_id"])
    op.create_table(
        "users",
        sa.Column("company_id", sa.Uuid(), nullable=False),
        sa.Column("full_name", sa.String(length=140), nullable=False),
        sa.Column("email", sa.String(length=254), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("role", sa.String(length=20), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint(
            "role IN ('admin', 'finance', 'manager')", name=op.f("ck_users_valid_role")
        ),
        sa.ForeignKeyConstraint(
            ["company_id"],
            ["companies.id"],
            name=op.f("fk_users_company_id_companies"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_users")),
        sa.UniqueConstraint("company_id", "email", name=op.f("uq_users_company_id_email")),
    )
    op.create_index(op.f("ix_users_company_id"), "users", ["company_id"])
    op.create_table(
        "invoices",
        sa.Column("supplier_id", sa.Uuid(), nullable=False),
        sa.Column("cost_center_id", sa.Uuid(), nullable=True),
        sa.Column("invoice_number", sa.String(length=80), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("category", sa.String(length=80), nullable=False),
        sa.Column("issue_date", sa.Date(), nullable=False),
        sa.Column("due_date", sa.Date(), nullable=False),
        sa.Column("amount", sa.Numeric(precision=14, scale=2), nullable=False),
        sa.Column("currency", sa.String(length=3), server_default="BRL", nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("source", sa.String(length=20), nullable=False),
        sa.Column("ai_confidence", sa.Numeric(precision=5, scale=4), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("company_id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint(
            "ai_confidence IS NULL OR (ai_confidence >= 0 AND ai_confidence <= 1)",
            name=op.f("ck_invoices_valid_ai_confidence"),
        ),
        sa.CheckConstraint("amount > 0", name=op.f("ck_invoices_positive_amount")),
        sa.CheckConstraint("char_length(currency) = 3", name=op.f("ck_invoices_valid_currency")),
        sa.CheckConstraint("due_date >= issue_date", name=op.f("ck_invoices_valid_date_range")),
        sa.CheckConstraint(
            "source IN ('manual', 'document', 'erp')", name=op.f("ck_invoices_valid_source")
        ),
        sa.CheckConstraint(
            "status IN ('pending', 'approved', 'paid', 'overdue', 'rejected')",
            name=op.f("ck_invoices_valid_status"),
        ),
        sa.ForeignKeyConstraint(
            ["company_id"],
            ["companies.id"],
            name=op.f("fk_invoices_company_id_companies"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["cost_center_id"],
            ["cost_centers.id"],
            name=op.f("fk_invoices_cost_center_id_cost_centers"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["supplier_id"],
            ["suppliers.id"],
            name=op.f("fk_invoices_supplier_id_suppliers"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_invoices")),
        sa.UniqueConstraint(
            "company_id",
            "supplier_id",
            "invoice_number",
            name=op.f("uq_invoices_company_id_supplier_id_invoice_number"),
        ),
    )
    op.create_index(op.f("ix_invoices_category"), "invoices", ["category"])
    op.create_index(op.f("ix_invoices_company_id"), "invoices", ["company_id"])
    op.create_index("ix_invoices_company_issue_date", "invoices", ["company_id", "issue_date"])
    op.create_index(
        "ix_invoices_company_status_due_date", "invoices", ["company_id", "status", "due_date"]
    )
    op.create_index(op.f("ix_invoices_cost_center_id"), "invoices", ["cost_center_id"])
    op.create_index(op.f("ix_invoices_supplier_id"), "invoices", ["supplier_id"])


def downgrade() -> None:
    op.drop_table("invoices")
    op.drop_table("users")
    op.drop_table("suppliers")
    op.drop_table("cost_centers")
    op.drop_table("companies")
    op.execute("DROP EXTENSION IF EXISTS vector")
