"""seed RBAC roles and permissions

Revision ID: b8f3b22e1c8a
Revises: eb9ea848b9d4
Create Date: 2026-07-06 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "b8f3b22e1c8a"
down_revision: Union[str, Sequence[str], None] = "eb9ea848b9d4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


PERMISSIONS = [
    ("Scenario View", "scenario:view", "Xem scenario"),
    ("Scenario Create", "scenario:create", "Tạo scenario mới"),
    ("Scenario Edit", "scenario:edit", "Sửa scenario"),
    ("Chat Start", "chat:start", "Bắt đầu chat session"),
    ("Vocab Manage", "vocab:manage", "CRUD vocab của chính mình"),
    ("Report View All", "report:view_all", "Xem toàn bộ analytics hệ thống"),
]

ROLES = [
    ("learner", "Default learner role"),
    ("admin", "System administrator"),
]

LEARNER_PERMISSION_CODES = {
    "scenario:view",
    "chat:start",
    "vocab:manage",
}



def _insert_permissions(conn) -> None:
    for name, code, description in PERMISSIONS:
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
            {"name": name, "code": code, "description": description},
        )



def _insert_roles(conn) -> None:
    for name, description in ROLES:
        conn.execute(
            sa.text(
                """
                INSERT INTO roles(name, description)
                VALUES (:name, :description)
                ON CONFLICT (name) DO UPDATE
                SET
                    description = EXCLUDED.description
                """
            ),
            {"name": name, "description": description},
        )



def _assign_permissions_to_roles(conn) -> None:
    permission_rows = conn.execute(sa.text("SELECT id, code FROM permissions")).fetchall()
    role_rows = conn.execute(sa.text("SELECT id, name FROM roles")).fetchall()

    permission_id_by_code = {row.code: row.id for row in permission_rows}
    role_id_by_name = {row.name: row.id for row in role_rows}

    learner_role_id = role_id_by_name.get("learner")
    admin_role_id = role_id_by_name.get("admin")

    if learner_role_id:
        for code in LEARNER_PERMISSION_CODES:
            permission_id = permission_id_by_code.get(code)
            if not permission_id:
                continue
            conn.execute(
                sa.text(
                    """
                    INSERT INTO role_permissions(role_id, permission_id)
                    VALUES (:role_id, :permission_id)
                    ON CONFLICT (role_id, permission_id) DO NOTHING
                    """
                ),
                {"role_id": learner_role_id, "permission_id": permission_id},
            )

    if admin_role_id:
        for permission_id in permission_id_by_code.values():
            conn.execute(
                sa.text(
                    """
                    INSERT INTO role_permissions(role_id, permission_id)
                    VALUES (:role_id, :permission_id)
                    ON CONFLICT (role_id, permission_id) DO NOTHING
                    """
                ),
                {"role_id": admin_role_id, "permission_id": permission_id},
            )



def upgrade() -> None:
    conn = op.get_bind()
    _insert_permissions(conn)
    _insert_roles(conn)
    _assign_permissions_to_roles(conn)



def downgrade() -> None:
    conn = op.get_bind()

    conn.execute(
        sa.text(
            """
            DELETE FROM role_permissions rp
            USING roles r
            WHERE rp.role_id = r.id
              AND r.name IN ('admin', 'learner')
            """
        )
    )

    conn.execute(
        sa.text(
            """
            DELETE FROM roles
            WHERE name IN ('admin', 'learner')
            """
        )
    )

    conn.execute(
        sa.text(
            """
            DELETE FROM permissions
            WHERE code IN (
                'scenario:view',
                'scenario:create',
                'scenario:edit',
                'chat:start',
                'vocab:manage',
                'report:view_all'
            )
            """
        )
    )
