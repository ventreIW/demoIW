"""seed 3 blank scenarios for demo sectors

Revision ID: 0003
Revises: 0002
Create Date: 2026-06-25
"""

from collections.abc import Sequence
from uuid import uuid4

from alembic import op

revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    ids = [str(uuid4()), str(uuid4()), str(uuid4())]
    cols = "id, name, sector, seed, parameters, source, status, created_at"
    rows = [
        f"('{ids[0]}', 'Manufactura — Demo', 'manufacturing', NULL, '{{}}', 'generated', 'inactive', NOW())",  # noqa: E501
        f"('{ids[1]}', 'Retail — Demo', 'retail', NULL, '{{}}', 'generated', 'inactive', NOW())",
        f"('{ids[2]}', 'Servicios Profesionales — Demo', 'professional_services', NULL, '{{}}', 'generated', 'inactive', NOW())",  # noqa: E501
    ]
    op.execute(f"INSERT INTO scenarios ({cols}) VALUES " + ", ".join(rows))


def downgrade() -> None:
    op.execute("DELETE FROM scenarios WHERE source = 'generated'")
