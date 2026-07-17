"""add passage column to quiz_questions

Revision ID: h8i9j0k1l2m3
Revises: g7h8i9j0k1l2
Create Date: 2026-07-17 15:30:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "h8i9j0k1l2m3"
down_revision: Union[str, Sequence[str], None] = "g7h8i9j0k1l2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "quiz_questions",
        sa.Column("passage", sa.TEXT(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("quiz_questions", "passage")
