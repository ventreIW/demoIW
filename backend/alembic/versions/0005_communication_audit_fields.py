"""communications: NFR-06 audit provenance

Revision ID: 0005
Revises: 0004
Create Date: 2026-08-20

NFR-06 requires every communication draft and send action to record timestamp, operator
identifier, model used and prompt version. Only the draft timestamp was stored (BUG-08).

All four columns are nullable, deliberately. Rows written before this migration genuinely do
not know which model wrote them or who initiated them; backfilling a plausible value would
falsify the audit record, which is worse than recording that the provenance is unknown. An
audit trail that invents its own history is not an audit trail.
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0005"
down_revision: str | None = "0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("communications", sa.Column("operator_id", sa.String(100), nullable=True))
    op.add_column("communications", sa.Column("model_used", sa.String(200), nullable=True))
    op.add_column("communications", sa.Column("prompt_version", sa.String(50), nullable=True))
    op.add_column(
        # TIMESTAMP(timezone=True) to match every other timestamp in 0002. The first
        # draft of this migration used a naive sa.DateTime(), which PostgreSQL would
        # have rejected on write (BUG-09). Amended rather than superseded: no database
        # anywhere had applied 0005 at the time of the change.
        "communications",
        sa.Column("sent_at", sa.TIMESTAMP(timezone=True), nullable=True),
    )

    # Audit queries filter by who and by when far more often than by anything else.
    op.create_index("ix_communications_operator_id", "communications", ["operator_id"])
    op.create_index("ix_communications_sent_at", "communications", ["sent_at"])


def downgrade() -> None:
    op.drop_index("ix_communications_sent_at", table_name="communications")
    op.drop_index("ix_communications_operator_id", table_name="communications")
    op.drop_column("communications", "sent_at")
    op.drop_column("communications", "prompt_version")
    op.drop_column("communications", "model_used")
    op.drop_column("communications", "operator_id")
