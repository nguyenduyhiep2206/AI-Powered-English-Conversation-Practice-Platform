"""add books table and book:manage permission

Revision ID: d7e2a91f4c30
Revises: c4a1e8f92b10
Create Date: 2026-07-07 08:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "d7e2a91f4c30"
down_revision: Union[str, Sequence[str], None] = "c4a1e8f92b10"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

book_status_enum = postgresql.ENUM(
    "uploaded",
    "processing",
    "ready",
    "failed",
    name="book_status_enum",
    create_type=False,
)
cefr_level_enum = postgresql.ENUM(
    "A1",
    "A2",
    "B1",
    "B2",
    "C1",
    name="cefr_level",
    create_type=False,
)


def _add_book_manage_permission(conn) -> None:
    conn.execute(
        sa.text(
            """
            INSERT INTO permissions(name, code, description)
            VALUES (:name, :code, :description)
            ON CONFLICT (code) DO UPDATE
            SET
                name = EXCLUDED.name,
                description = EXCLUDED.description
            """
        ),
        {
            "name": "Book Manage",
            "code": "book:manage",
            "description": "Upload and manage PDF books",
        },
    )

    admin_role = conn.execute(
        sa.text("SELECT id FROM roles WHERE name = 'admin'")
    ).fetchone()
    permission = conn.execute(
        sa.text("SELECT id FROM permissions WHERE code = 'book:manage'")
    ).fetchone()

    if admin_role and permission:
        conn.execute(
            sa.text(
                """
                INSERT INTO role_permissions(role_id, permission_id)
                VALUES (:role_id, :permission_id)
                ON CONFLICT (role_id, permission_id) DO NOTHING
                """
            ),
            {"role_id": admin_role.id, "permission_id": permission.id},
        )


def upgrade() -> None:
    book_status_enum.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "books",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.String(length=2000), nullable=True),
        sa.Column("cefr_level", cefr_level_enum, nullable=True),
        sa.Column("file_path", sa.String(length=500), nullable=False),
        sa.Column("file_size", sa.BigInteger(), nullable=False),
        sa.Column("page_count", sa.Integer(), nullable=True),
        sa.Column(
            "status",
            book_status_enum,
            server_default="uploaded",
            nullable=False,
        ),
        sa.Column("uploaded_by", sa.BigInteger(), nullable=True),
        sa.Column("chunk_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["uploaded_by"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )

    conn = op.get_bind()
    _add_book_manage_permission(conn)


def downgrade() -> None:
    conn = op.get_bind()

    conn.execute(
        sa.text(
            """
            DELETE FROM role_permissions rp
            USING roles r, permissions p
            WHERE rp.role_id = r.id
              AND rp.permission_id = p.id
              AND r.name = 'admin'
              AND p.code = 'book:manage'
            """
        )
    )
    conn.execute(sa.text("DELETE FROM permissions WHERE code = 'book:manage'"))

    op.drop_table("books")
    book_status_enum.drop(op.get_bind(), checkfirst=True)
