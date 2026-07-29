"""add skill_lessons and user_lesson_progress for mini-unit learn

Revision ID: n3o4p5q6r7s8
Revises: m2n3o4p5q6r7
Create Date: 2026-07-29 09:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect
from sqlalchemy.dialects import postgresql

revision: str = "n3o4p5q6r7s8"
down_revision: Union[str, Sequence[str], None] = "m2n3o4p5q6r7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_table(name: str) -> bool:
    bind = op.get_bind()
    return name in inspect(bind).get_table_names()


def _has_index(table: str, index_name: str) -> bool:
    bind = op.get_bind()
    return any(ix["name"] == index_name for ix in inspect(bind).get_indexes(table))


def upgrade() -> None:
    # Tables may already exist from deleted revision k1l2m3n4o5p6 (slide Learn).
    if not _has_table("skill_lessons"):
        op.create_table(
            "skill_lessons",
            sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
            sa.Column("skill_id", sa.BigInteger(), nullable=False),
            sa.Column("title", sa.String(length=500), nullable=False),
            sa.Column("objective", sa.Text(), nullable=False),
            sa.Column("content", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
            sa.Column(
                "source", sa.String(length=20), nullable=False, server_default="llm_reviewed"
            ),
            sa.Column("status", sa.String(length=20), nullable=False, server_default="draft"),
            sa.Column("book_source_id", sa.BigInteger(), nullable=True),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.text("now()"),
                nullable=False,
            ),
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                server_default=sa.text("now()"),
                nullable=False,
            ),
            sa.ForeignKeyConstraint(
                ["book_source_id"], ["book_skill_sources.id"], ondelete="SET NULL"
            ),
            sa.ForeignKeyConstraint(
                ["skill_id"], ["learning_skills.id"], ondelete="CASCADE"
            ),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("skill_id", name="uq_skill_lessons_skill_id"),
        )
    if _has_table("skill_lessons") and not _has_index(
        "skill_lessons", "ix_skill_lessons_skill_id"
    ):
        op.create_index("ix_skill_lessons_skill_id", "skill_lessons", ["skill_id"])

    if not _has_table("user_lesson_progress"):
        op.create_table(
            "user_lesson_progress",
            sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
            sa.Column("user_id", sa.BigInteger(), nullable=False),
            sa.Column("skill_id", sa.BigInteger(), nullable=False),
            sa.Column(
                "completed_at",
                sa.DateTime(timezone=True),
                server_default=sa.text("now()"),
                nullable=False,
            ),
            sa.ForeignKeyConstraint(
                ["skill_id"], ["learning_skills.id"], ondelete="CASCADE"
            ),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("user_id", "skill_id", name="uq_user_lesson_progress"),
        )
    if _has_table("user_lesson_progress") and not _has_index(
        "user_lesson_progress", "ix_user_lesson_progress_user_id"
    ):
        op.create_index(
            "ix_user_lesson_progress_user_id", "user_lesson_progress", ["user_id"]
        )
    if _has_table("user_lesson_progress") and not _has_index(
        "user_lesson_progress", "ix_user_lesson_progress_skill_id"
    ):
        op.create_index(
            "ix_user_lesson_progress_skill_id", "user_lesson_progress", ["skill_id"]
        )


def downgrade() -> None:
    if _has_table("user_lesson_progress"):
        op.drop_table("user_lesson_progress")
    if _has_table("skill_lessons"):
        op.drop_table("skill_lessons")
