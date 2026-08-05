"""add skill_lessons.pack_index for LessonPack

Revision ID: q6r7s8t9u0v1
Revises: p5q6r7s8t9u0
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision: str = "q6r7s8t9u0v1"
down_revision: Union[str, Sequence[str], None] = "p5q6r7s8t9u0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_column(table: str, column: str) -> bool:
    bind = op.get_bind()
    return any(c["name"] == column for c in inspect(bind).get_columns(table))


def _has_unique(table: str, name: str) -> bool:
    bind = op.get_bind()
    return any(u["name"] == name for u in inspect(bind).get_unique_constraints(table))


def upgrade() -> None:
    if not _has_column("skill_lessons", "pack_index"):
        op.add_column(
            "skill_lessons",
            sa.Column("pack_index", sa.Integer(), nullable=False, server_default="0"),
        )
    if _has_unique("skill_lessons", "uq_skill_lessons_skill_id"):
        op.drop_constraint("uq_skill_lessons_skill_id", "skill_lessons", type_="unique")
    if not _has_unique("skill_lessons", "uq_skill_lessons_skill_pack"):
        op.create_unique_constraint(
            "uq_skill_lessons_skill_pack",
            "skill_lessons",
            ["skill_id", "pack_index"],
        )

    if "user_lesson_pack_progress" not in inspect(op.get_bind()).get_table_names():
        op.create_table(
            "user_lesson_pack_progress",
            sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
            sa.Column("user_id", sa.BigInteger(), nullable=False),
            sa.Column("skill_id", sa.BigInteger(), nullable=False),
            sa.Column("pack_index", sa.Integer(), nullable=False),
            sa.Column(
                "completed_at",
                sa.DateTime(timezone=True),
                server_default=sa.text("now()"),
                nullable=False,
            ),
            sa.ForeignKeyConstraint(["skill_id"], ["learning_skills.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint(
                "user_id",
                "skill_id",
                "pack_index",
                name="uq_user_lesson_pack_progress",
            ),
        )
        op.create_index(
            "ix_user_lesson_pack_progress_user_id",
            "user_lesson_pack_progress",
            ["user_id"],
        )
        op.create_index(
            "ix_user_lesson_pack_progress_skill_id",
            "user_lesson_pack_progress",
            ["skill_id"],
        )


def downgrade() -> None:
    bind = op.get_bind()
    tables = inspect(bind).get_table_names()
    if "user_lesson_pack_progress" in tables:
        op.drop_index(
            "ix_user_lesson_pack_progress_skill_id",
            table_name="user_lesson_pack_progress",
        )
        op.drop_index(
            "ix_user_lesson_pack_progress_user_id",
            table_name="user_lesson_pack_progress",
        )
        op.drop_table("user_lesson_pack_progress")

    if _has_unique("skill_lessons", "uq_skill_lessons_skill_pack"):
        op.drop_constraint("uq_skill_lessons_skill_pack", "skill_lessons", type_="unique")
    if _has_column("skill_lessons", "pack_index"):
        op.drop_column("skill_lessons", "pack_index")
    if not _has_unique("skill_lessons", "uq_skill_lessons_skill_id"):
        op.create_unique_constraint(
            "uq_skill_lessons_skill_id", "skill_lessons", ["skill_id"]
        )
