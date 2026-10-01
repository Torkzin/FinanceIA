"""Add ERP integration checkpoints and sync logs.

Revision ID: 20260930_0007
Revises: 20260930_0006
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260930_0007"
down_revision: str | None = "20260930_0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "integration_connections",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("company_id", sa.Uuid(), nullable=False),
        sa.Column("provider", sa.String(40), nullable=False),
        sa.Column("adapter", sa.String(80), nullable=False),
        sa.Column("status", sa.String(20), server_default="active", nullable=False),
        sa.Column("checkpoint", sa.String(160)),
        sa.Column("last_sync_at", sa.DateTime(timezone=True)),
        sa.Column("last_sync_status", sa.String(20)),
        sa.Column("last_summary", sa.JSON()),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "status IN ('active', 'inactive')",
            name="ck_integration_connections_valid_status",
        ),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("company_id", "provider"),
    )
    op.create_index(
        "ix_integration_connections_company_id", "integration_connections", ["company_id"]
    )

    op.create_table(
        "integration_sync_runs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("company_id", sa.Uuid(), nullable=False),
        sa.Column("connection_id", sa.Uuid(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("summary", sa.JSON(), nullable=False),
        sa.Column("error_message", sa.Text()),
        sa.CheckConstraint(
            "status IN ('completed', 'failed')",
            name="ck_integration_sync_runs_valid_status",
        ),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["connection_id"], ["integration_connections.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_integration_sync_runs_company_id", "integration_sync_runs", ["company_id"])
    op.create_index(
        "ix_integration_sync_runs_company_started",
        "integration_sync_runs",
        ["company_id", "started_at"],
    )


def downgrade() -> None:
    op.drop_table("integration_sync_runs")
    op.drop_table("integration_connections")
