"""client.generation_index — stable ordering key for reproducible scoring

Revision ID: 0004
Revises: 0003
Create Date: 2026-08-20

`clients.id` is a random surrogate key assigned by the persistence layer. OutcomeLabeller
applied a seeded random draw along an axis sorted by that id, so the same seed produced a
different label assignment — and therefore a different model — on every run (BUG-05).

This column carries the client's position in its scenario's generation sequence, giving the
labeller a stable axis to order by. See ADR-011.

Backfill is deterministic: existing rows are numbered by `id` within each scenario. That
reproduces the ordering those scenarios were *already* scored under, so historical scores stay
consistent with their data rather than being silently re-based.
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0004"
down_revision: str | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Nullable first so the add succeeds against populated tables.
    op.add_column("clients", sa.Column("generation_index", sa.Integer(), nullable=True))

    op.execute(
        """
        UPDATE clients
        SET generation_index = ordered.rn
        FROM (
            SELECT id,
                   ROW_NUMBER() OVER (PARTITION BY scenario_id ORDER BY id) - 1 AS rn
            FROM clients
        ) AS ordered
        WHERE clients.id = ordered.id
        """
    )

    op.alter_column("clients", "generation_index", nullable=False)
    op.create_index(
        "ix_clients_scenario_generation_index",
        "clients",
        ["scenario_id", "generation_index"],
    )


def downgrade() -> None:
    op.drop_index("ix_clients_scenario_generation_index", table_name="clients")
    op.drop_column("clients", "generation_index")
