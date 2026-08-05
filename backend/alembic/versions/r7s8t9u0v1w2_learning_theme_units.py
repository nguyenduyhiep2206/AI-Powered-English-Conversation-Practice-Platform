"""add learning_theme_units catalog tables

Revision ID: r7s8t9u0v1w2
Revises: q6r7s8t9u0v1
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect
from sqlalchemy.dialects import postgresql

revision: str = "r7s8t9u0v1w2"
down_revision: Union[str, Sequence[str], None] = "q6r7s8t9u0v1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

cefr_level = postgresql.ENUM(
    "A1",
    "A2",
    "B1",
    "B2",
    "C1",
    name="cefr_level",
    create_type=False,
)


def upgrade() -> None:
    bind = op.get_bind()
    tables = inspect(bind).get_table_names()
    if "learning_theme_units" not in tables:
        op.create_table(
            "learning_theme_units",
            sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
            sa.Column("slug", sa.String(length=120), nullable=False),
            sa.Column("cefr_level", cefr_level, nullable=False),
            sa.Column("title", sa.String(length=500), nullable=False),
            sa.Column("can_do", sa.Text(), nullable=False),
            sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
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
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("slug", "cefr_level", name="uq_theme_units_slug_level"),
        )
        op.create_index(
            "ix_learning_theme_units_cefr_level",
            "learning_theme_units",
            ["cefr_level"],
        )

    if "theme_unit_skills" not in inspect(bind).get_table_names():
        op.create_table(
            "theme_unit_skills",
            sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
            sa.Column("theme_unit_id", sa.BigInteger(), nullable=False),
            sa.Column("skill_id", sa.BigInteger(), nullable=False),
            sa.Column("position", sa.Integer(), nullable=False, server_default="0"),
            sa.ForeignKeyConstraint(
                ["skill_id"], ["learning_skills.id"], ondelete="CASCADE"
            ),
            sa.ForeignKeyConstraint(
                ["theme_unit_id"], ["learning_theme_units.id"], ondelete="CASCADE"
            ),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint(
                "theme_unit_id", "skill_id", name="uq_theme_unit_skill"
            ),
            sa.UniqueConstraint("skill_id", name="uq_theme_unit_skills_skill_id"),
        )
        op.create_index(
            "ix_theme_unit_skills_theme_unit_id",
            "theme_unit_skills",
            ["theme_unit_id"],
        )
        op.create_index(
            "ix_theme_unit_skills_skill_id",
            "theme_unit_skills",
            ["skill_id"],
        )


def downgrade() -> None:
    bind = op.get_bind()
    tables = inspect(bind).get_table_names()
    if "theme_unit_skills" in tables:
        op.drop_index("ix_theme_unit_skills_skill_id", table_name="theme_unit_skills")
        op.drop_index(
            "ix_theme_unit_skills_theme_unit_id", table_name="theme_unit_skills"
        )
        op.drop_table("theme_unit_skills")
    if "learning_theme_units" in tables:
        op.drop_index(
            "ix_learning_theme_units_cefr_level", table_name="learning_theme_units"
        )
        op.drop_table("learning_theme_units")
