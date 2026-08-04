"""nullable roadmap_step_id on tutor_sessions for catalog-only starts

Revision ID: u0v1w2x3y4z5
Revises: t9u0v1w2x3y4
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "u0v1w2x3y4z5"
down_revision: Union[str, Sequence[str], None] = "t9u0v1w2x3y4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column(
        "tutor_sessions",
        "roadmap_step_id",
        existing_type=sa.BigInteger(),
        nullable=True,
    )


def downgrade() -> None:
    op.execute("DELETE FROM tutor_sessions WHERE roadmap_step_id IS NULL")
    op.alter_column(
        "tutor_sessions",
        "roadmap_step_id",
        existing_type=sa.BigInteger(),
        nullable=False,
    )
