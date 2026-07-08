"""add file_public_id to books (Cloudinary storage)

Revision ID: e5f3c2b8a41d
Revises: d7e2a91f4c30
Create Date: 2026-07-08 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "e5f3c2b8a41d"
down_revision: Union[str, Sequence[str], None] = "d7e2a91f4c30"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "books",
        sa.Column("file_public_id", sa.String(length=500), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("books", "file_public_id")
