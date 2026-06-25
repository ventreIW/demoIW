"""domain schema — all 7 entity tables

Revision ID: 0002
Revises: 0001
Create Date: 2026-06-25
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "scenarios",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("sector", sa.String(50), nullable=False),
        sa.Column("seed", sa.Integer, nullable=True),
        sa.Column(
            "parameters",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default="{}",
        ),
        sa.Column("source", sa.String(50), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="inactive"),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )

    # Partial unique index: at most one active scenario at a time (ADR-002)
    op.execute(
        """
        CREATE UNIQUE INDEX uix_scenarios_active
        ON scenarios (status)
        WHERE status = 'active'
        """
    )

    op.create_table(
        "clients",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column(
            "scenario_id",
            postgresql.UUID(as_uuid=False),
            sa.ForeignKey("scenarios.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("sector_description", sa.String(500), nullable=True),
        sa.Column("payment_history_pattern", sa.String(50), nullable=False),
    )

    op.create_table(
        "invoices",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column(
            "client_id",
            postgresql.UUID(as_uuid=False),
            sa.ForeignKey("clients.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("folio", sa.String(50), nullable=False),
        sa.Column("amount", sa.Float, nullable=False),
        sa.Column("issue_date", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("due_date", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("days_overdue", sa.Integer, nullable=False, server_default="0"),
        sa.Column("status", sa.String(50), nullable=False),
    )

    op.create_table(
        "payments",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column(
            "invoice_id",
            postgresql.UUID(as_uuid=False),
            sa.ForeignKey("invoices.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("amount", sa.Float, nullable=False),
        sa.Column("payment_date", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("method", sa.String(50), nullable=False),
    )

    op.create_table(
        "scores",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column(
            "client_id",
            postgresql.UUID(as_uuid=False),
            sa.ForeignKey("clients.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "scenario_id",
            postgresql.UUID(as_uuid=False),
            sa.ForeignKey("scenarios.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("score_value", sa.Float, nullable=False),
        sa.Column("category", sa.String(20), nullable=False),
        sa.Column("explanation", sa.Text, nullable=False),
        sa.Column("scored_at", sa.TIMESTAMP(timezone=True), nullable=False),
    )

    op.create_table(
        "communications",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column(
            "client_id",
            postgresql.UUID(as_uuid=False),
            sa.ForeignKey("clients.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "scenario_id",
            postgresql.UUID(as_uuid=False),
            sa.ForeignKey("scenarios.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("channel", sa.String(20), nullable=False),
        sa.Column("tone", sa.String(20), nullable=False),
        sa.Column("draft_text", sa.Text, nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False),
    )

    op.create_table(
        "contact_results",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column(
            "client_id",
            postgresql.UUID(as_uuid=False),
            sa.ForeignKey("clients.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "communication_id",
            postgresql.UUID(as_uuid=False),
            sa.ForeignKey("communications.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("result_type", sa.String(50), nullable=False),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("recorded_at", sa.TIMESTAMP(timezone=True), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("contact_results")
    op.drop_table("communications")
    op.drop_table("scores")
    op.drop_table("payments")
    op.drop_table("invoices")
    op.drop_table("clients")
    op.execute("DROP INDEX IF EXISTS uix_scenarios_active")
    op.drop_table("scenarios")
