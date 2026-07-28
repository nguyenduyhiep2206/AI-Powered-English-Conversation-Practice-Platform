"""Reshape placement attempts for timed TOEIC R+W sessions

Revision ID: m2n3o4p5q6r7
Revises: m1n2o3p4q5r6
Create Date: 2026-07-28 14:30:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "m2n3o4p5q6r7"
down_revision: Union[str, Sequence[str], None] = "m1n2o3p4q5r6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "placement_attempts",
        sa.Column("form_snapshot", postgresql.JSON(astext_type=sa.Text()), nullable=True),
    )
    op.add_column(
        "placement_attempts",
        sa.Column("section", sa.String(length=20), nullable=False, server_default="reading"),
    )
    op.add_column(
        "placement_attempts",
        sa.Column("section_ends_at", sa.TIMESTAMP(timezone=True), nullable=True),
    )
    op.add_column("placement_attempts", sa.Column("reading_raw", sa.Integer(), nullable=True))
    op.add_column("placement_attempts", sa.Column("reading_scale", sa.Integer(), nullable=True))
    op.add_column("placement_attempts", sa.Column("writing_raw", sa.Float(), nullable=True))
    op.add_column("placement_attempts", sa.Column("writing_scale", sa.Integer(), nullable=True))

    op.alter_column("placement_attempts", "ability_index", existing_type=sa.Float(), nullable=True)
    op.alter_column("placement_attempts", "confidence", existing_type=sa.Float(), nullable=True)

    op.add_column("placement_attempt_answers", sa.Column("score", sa.Float(), nullable=True))
    op.add_column(
        "placement_attempt_answers",
        sa.Column("ai_scores", postgresql.JSON(astext_type=sa.Text()), nullable=True),
    )
    op.add_column("placement_attempt_answers", sa.Column("ai_feedback", sa.Text(), nullable=True))

    op.alter_column(
        "placement_attempt_answers", "skill_id", existing_type=sa.BigInteger(), nullable=True
    )
    op.alter_column(
        "placement_attempt_answers",
        "cefr_level",
        existing_type=postgresql.ENUM(name="cefr_level", create_type=False),
        nullable=True,
    )
    op.alter_column(
        "placement_attempt_answers", "is_correct", existing_type=sa.Boolean(), nullable=True
    )
    op.alter_column(
        "placement_attempt_answers", "ability_after", existing_type=sa.Float(), nullable=True
    )
    op.alter_column(
        "placement_attempt_answers", "confidence_after", existing_type=sa.Float(), nullable=True
    )


def downgrade() -> None:
    op.alter_column(
        "placement_attempt_answers", "confidence_after", existing_type=sa.Float(), nullable=False
    )
    op.alter_column(
        "placement_attempt_answers", "ability_after", existing_type=sa.Float(), nullable=False
    )
    op.alter_column(
        "placement_attempt_answers", "is_correct", existing_type=sa.Boolean(), nullable=False
    )
    op.alter_column(
        "placement_attempt_answers",
        "cefr_level",
        existing_type=postgresql.ENUM(name="cefr_level", create_type=False),
        nullable=False,
    )
    op.alter_column(
        "placement_attempt_answers", "skill_id", existing_type=sa.BigInteger(), nullable=False
    )
    op.drop_column("placement_attempt_answers", "ai_feedback")
    op.drop_column("placement_attempt_answers", "ai_scores")
    op.drop_column("placement_attempt_answers", "score")

    op.alter_column("placement_attempts", "confidence", existing_type=sa.Float(), nullable=False)
    op.alter_column("placement_attempts", "ability_index", existing_type=sa.Float(), nullable=False)
    op.drop_column("placement_attempts", "writing_scale")
    op.drop_column("placement_attempts", "writing_raw")
    op.drop_column("placement_attempts", "reading_scale")
    op.drop_column("placement_attempts", "reading_raw")
    op.drop_column("placement_attempts", "section_ends_at")
    op.drop_column("placement_attempts", "section")
    op.drop_column("placement_attempts", "form_snapshot")
