"""add learning_skills.difficulty_in_level

Revision ID: i9j0k1l2m3n4
Revises: h8i9j0k1l2m3
Create Date: 2026-07-20 11:20:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "i9j0k1l2m3n4"
down_revision: Union[str, Sequence[str], None] = "h8i9j0k1l2m3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "learning_skills",
        sa.Column("difficulty_in_level", sa.SmallInteger(), nullable=True),
    )
    # Backfill from non-excluded book sources: avg of position-based 1..10 per skill
    op.execute(
        """
        UPDATE learning_skills AS ls
        SET difficulty_in_level = sub.diff
        FROM (
            SELECT
                bss.skill_id,
                GREATEST(
                    1,
                    LEAST(
                        10,
                        CAST(
                            ROUND(
                                AVG(
                                    CASE
                                        WHEN max_u.max_idx IS NULL OR max_u.max_idx = 0 THEN 1
                                        ELSE 1 + (
                                            9.0 * COALESCE(bsp.unit_index, 0)
                                            / max_u.max_idx
                                        )
                                    END
                                )
                            ) AS INTEGER
                        )
                    )
                ) AS diff
            FROM book_skill_sources bss
            JOIN book_structure_preview bsp ON bsp.id = bss.unit_id
            JOIN (
                SELECT book_id, MAX(unit_index) AS max_idx
                FROM book_structure_preview
                GROUP BY book_id
            ) AS max_u ON max_u.book_id = bss.book_id
            WHERE bss.is_excluded = false
            GROUP BY bss.skill_id
        ) AS sub
        WHERE ls.id = sub.skill_id
          AND ls.difficulty_in_level IS NULL
        """
    )
    # Skills with no sources (or failed join): default mid-level
    op.execute(
        "UPDATE learning_skills SET difficulty_in_level = 5 WHERE difficulty_in_level IS NULL"
    )


def downgrade() -> None:
    op.drop_column("learning_skills", "difficulty_in_level")
