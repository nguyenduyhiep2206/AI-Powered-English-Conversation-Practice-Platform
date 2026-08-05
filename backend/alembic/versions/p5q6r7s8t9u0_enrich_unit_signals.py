"""enrich unit signals on structure preview

Revision ID: p5q6r7s8t9u0
Revises: o4p5q6r7s8t9
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "p5q6r7s8t9u0"
down_revision = "o4p5q6r7s8t9"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "book_structure_preview",
        sa.Column("language_focus", sa.String(length=1000), nullable=True),
    )
    op.add_column(
        "book_structure_preview",
        sa.Column(
            "grammar_cues",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
    )
    op.add_column(
        "book_structure_preview",
        sa.Column(
            "vocab_cues",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
    )
    op.add_column(
        "book_structure_preview",
        sa.Column("content_summary", sa.String(length=2000), nullable=True),
    )
    op.add_column(
        "book_structure_preview",
        sa.Column("enrichment_status", sa.String(length=20), nullable=True),
    )
    op.add_column(
        "book_structure_preview",
        sa.Column("enriched_at", sa.TIMESTAMP(timezone=True), nullable=True),
    )
    op.add_column(
        "book_structure_preview",
        sa.Column("enrichment_source", sa.String(length=20), nullable=True),
    )
    op.add_column(
        "book_structure_preview",
        sa.Column("enrichment_method", sa.String(length=32), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("book_structure_preview", "enrichment_method")
    op.drop_column("book_structure_preview", "enrichment_source")
    op.drop_column("book_structure_preview", "enriched_at")
    op.drop_column("book_structure_preview", "enrichment_status")
    op.drop_column("book_structure_preview", "content_summary")
    op.drop_column("book_structure_preview", "vocab_cues")
    op.drop_column("book_structure_preview", "grammar_cues")
    op.drop_column("book_structure_preview", "language_focus")
