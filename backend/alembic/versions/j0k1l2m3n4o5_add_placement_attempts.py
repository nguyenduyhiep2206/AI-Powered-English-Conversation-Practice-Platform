"""add placement_attempts and placement_attempt_answers

Revision ID: j0k1l2m3n4o5
Revises: i9j0k1l2m3n4
Create Date: 2026-07-23 11:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "j0k1l2m3n4o5"
down_revision: Union[str, Sequence[str], None] = "i9j0k1l2m3n4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

placement_attempt_status_enum = postgresql.ENUM(
    "in_progress",
    "completed",
    "abandoned",
    name="placement_attempt_status_enum",
    create_type=False,
)


def upgrade() -> None:
    placement_attempt_status_enum.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "placement_attempts",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("status", placement_attempt_status_enum, nullable=False),
        sa.Column("ability_index", sa.Float(), nullable=False, server_default="1.0"),
        sa.Column("confidence", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("questions_asked", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "seen_question_ids",
            postgresql.JSON(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::json"),
        ),
        sa.Column("current_question_id", sa.BigInteger(), nullable=True),
        sa.Column("weak_point_bias", sa.String(length=50), nullable=True),
        sa.Column("result_level", postgresql.ENUM(name="cefr_level", create_type=False), nullable=True),
        sa.Column("result_sublevel", sa.SmallInteger(), nullable=True),
        sa.Column(
            "started_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("completed_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["current_question_id"], ["quiz_questions.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_placement_attempts_user_id"), "placement_attempts", ["user_id"], unique=False
    )

    op.create_table(
        "placement_attempt_answers",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("attempt_id", sa.BigInteger(), nullable=False),
        sa.Column("question_id", sa.BigInteger(), nullable=False),
        sa.Column("skill_id", sa.BigInteger(), nullable=False),
        sa.Column(
            "cefr_level",
            postgresql.ENUM(name="cefr_level", create_type=False),
            nullable=False,
        ),
        sa.Column("given_answer", sa.Text(), nullable=False),
        sa.Column("is_correct", sa.Boolean(), nullable=False),
        sa.Column("ability_after", sa.Float(), nullable=False),
        sa.Column("confidence_after", sa.Float(), nullable=False),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["attempt_id"], ["placement_attempts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["question_id"], ["quiz_questions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("attempt_id", "question_id", name="uq_placement_attempt_question"),
    )


def downgrade() -> None:
    op.drop_table("placement_attempt_answers")
    op.drop_index(op.f("ix_placement_attempts_user_id"), table_name="placement_attempts")
    op.drop_table("placement_attempts")
    placement_attempt_status_enum.drop(op.get_bind(), checkfirst=True)
