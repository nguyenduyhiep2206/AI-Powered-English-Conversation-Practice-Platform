"""add book_type, detection_method, needs_review status

Revision ID: f1a2b3c4d5e6
Revises: e5f3c2b8a41d
Create Date: 2026-07-09 14:15:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "f1a2b3c4d5e6"
down_revision: Union[str, Sequence[str], None] = "e5f3c2b8a41d"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

book_type_enum = postgresql.ENUM(
    "grammar_textbook",
    "reading_practice",
    "test_bank",
    "freeform",
    name="book_type_enum",
    create_type=False,
)


def upgrade() -> None:
    book_type_enum.create(op.get_bind(), checkfirst=True)

    op.execute(sa.text("ALTER TYPE book_status_enum ADD VALUE IF NOT EXISTS 'needs_review'"))

    op.add_column(
        "books",
        sa.Column(
            "book_type",
            book_type_enum,
            server_default="freeform",
            nullable=False,
        ),
    )
    op.add_column(
        "books",
        sa.Column("detection_method", sa.String(length=50), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("books", "detection_method")
    op.drop_column("books", "book_type")
    book_type_enum.drop(op.get_bind(), checkfirst=True)
    # PostgreSQL does not support removing individual enum values from book_status_enum.
