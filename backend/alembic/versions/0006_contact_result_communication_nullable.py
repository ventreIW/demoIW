"""contact_results.communication_id: NOT NULL -> NULL

Revision ID: 0006
Revises: 0005
Create Date: 2026-08-20

Migration 0002 declared this column NOT NULL; the ORM has always declared it
``Mapped[str | None]``. The ORM is right: a contact result records that the operator reached
the client, and the common case is a phone call made *before* any communication draft exists.
Requiring a linked communication makes the ordinary workflow impossible.

Nothing caught it because no test ever ran against a database built by these migrations —
SQLite builds its schema from the ORM via ``create_all``, where the constraint does not exist.
Found by E6's M4 on its first execution, behind two other divergences (BUG-09).

Written as a new revision rather than by amending 0002: 0002 has been in the repository since
E2 and may have been applied in an environment this session cannot see. Altering forward is
correct in either case.
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0006"
down_revision: str | None = "0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.alter_column(
        "contact_results",
        "communication_id",
        existing_type=sa.UUID(),
        nullable=True,
    )


def downgrade() -> None:
    # Reversing this is only safe while no row has a null communication_id; rows recorded
    # from a phone call legitimately do. Delete-then-restore would destroy real audit data,
    # so the downgrade restores the constraint and will fail loudly if such rows exist —
    # which is the correct outcome rather than silent data loss.
    op.alter_column(
        "contact_results",
        "communication_id",
        existing_type=sa.UUID(),
        nullable=False,
    )
