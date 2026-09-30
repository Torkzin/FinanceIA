"""Add explainable financial anomalies.

Revision ID: 20260930_0006
Revises: 20260930_0005
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "20260930_0006"
down_revision: str | None = "20260930_0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "anomalies",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("company_id", sa.Uuid(), nullable=False),
        sa.Column("related_invoice_id", sa.Uuid(), nullable=False),
        sa.Column("anomaly_type", sa.String(60), nullable=False),
        sa.Column("severity", sa.String(12), nullable=False),
        sa.Column("explanation", sa.Text(), nullable=False),
        sa.Column("metrics", postgresql.JSONB(), nullable=False),
        sa.Column("status", sa.String(20), server_default="open", nullable=False),
        sa.Column("detected_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ai_analysis", sa.Text()),
        sa.Column("ai_provider", sa.String(40)),
        sa.Column("ai_model", sa.String(100)),
        sa.Column("analyzed_at", sa.DateTime(timezone=True)),
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
            "severity IN ('low', 'medium', 'high')", name="ck_anomalies_valid_severity"
        ),
        sa.CheckConstraint(
            "status IN ('open', 'reviewed', 'dismissed')", name="ck_anomalies_valid_status"
        ),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["related_invoice_id"], ["invoices.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("company_id", "related_invoice_id", "anomaly_type"),
    )
    op.create_index("ix_anomalies_company_id", "anomalies", ["company_id"])
    op.create_index("ix_anomalies_related_invoice_id", "anomalies", ["related_invoice_id"])
    op.create_index("ix_anomalies_anomaly_type", "anomalies", ["anomaly_type"])
    op.create_index("ix_anomalies_severity", "anomalies", ["severity"])


def downgrade() -> None:
    op.drop_table("anomalies")
