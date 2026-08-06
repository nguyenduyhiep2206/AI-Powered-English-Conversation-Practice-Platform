"""Add skill drill question types to quiz_question_type_enum

Revision ID: n2o3p4q5r6s7
Revises: v1w2x3y4z5a6
Create Date: 2026-08-06 10:10:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "n2o3p4q5r6s7"
down_revision: Union[str, Sequence[str], None] = "v1w2x3y4z5a6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_NEW_QUESTION_TYPES = ("sentence_build", "matching", "multi_select")


def upgrade() -> None:
    for value in _NEW_QUESTION_TYPES:
        op.execute(
            sa.text(
                f"ALTER TYPE quiz_question_type_enum ADD VALUE IF NOT EXISTS '{value}'"
            )
        )


def downgrade() -> None:
    # PostgreSQL does not support removing individual enum values from quiz_question_type_enum.
    pass
