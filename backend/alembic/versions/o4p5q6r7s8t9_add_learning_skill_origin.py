"""add learning_skills.origin

Revision ID: o4p5q6r7s8t9
Revises: n3o4p5q6r7s8
"""

from alembic import op
import sqlalchemy as sa

revision = "o4p5q6r7s8t9"
down_revision = "n3o4p5q6r7s8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "learning_skills",
        sa.Column("origin", sa.String(length=20), nullable=False, server_default="legacy"),
    )


def downgrade() -> None:
    op.drop_column("learning_skills", "origin")
