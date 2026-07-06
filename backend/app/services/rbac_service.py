from __future__ import annotations

import json
from typing import Any

from redis import asyncio as redis
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.auth import PermissionDB, RoleDB, role_permissions_table, user_roles_table
from app.models.user import UserDB
from app.core.config import settings


def _permissions_cache_key(user_id: int) -> str:
    return f"user:{user_id}:permissions"


async def invalidate_user_permissions_cache(user_id: int, r: redis.Redis) -> None:
    await r.delete(_permissions_cache_key(user_id))


async def invalidate_many_user_permissions_cache(user_ids: list[int], r: redis.Redis) -> None:
    if not user_ids:
        return
    keys = [_permissions_cache_key(user_id) for user_id in user_ids]
    await r.delete(*keys)


async def _fetch_roles_and_permissions_from_db(db: AsyncSession, user_id: int) -> dict[str, list[str]]:
    role_stmt = (
        select(RoleDB.name)
        .join(user_roles_table, user_roles_table.c.role_id == RoleDB.id)
        .where(user_roles_table.c.user_id == user_id)
        .distinct()
    )
    permission_stmt = (
        select(PermissionDB.code)
        .join(role_permissions_table, role_permissions_table.c.permission_id == PermissionDB.id)
        .join(user_roles_table, user_roles_table.c.role_id == role_permissions_table.c.role_id)
        .where(user_roles_table.c.user_id == user_id)
        .distinct()
    )

    role_result = await db.execute(role_stmt)
    permission_result = await db.execute(permission_stmt)

    roles = sorted({name for name in role_result.scalars().all() if name})
    permissions = sorted({code for code in permission_result.scalars().all() if code})
    return {"roles": roles, "permissions": permissions}


async def get_user_roles_and_permissions(db: AsyncSession, r: redis.Redis,user_id: int,) -> dict[str, list[str]]:
    cache_key = _permissions_cache_key(user_id)
    cached = await r.get(cache_key)
    if cached:
        try:
            payload: Any = json.loads(cached)
            roles = payload.get("roles", [])
            permissions = payload.get("permissions", [])
            if isinstance(roles, list) and isinstance(permissions, list):
                return {"roles": sorted(set(roles)), "permissions": sorted(set(permissions))}
        except (TypeError, ValueError, json.JSONDecodeError):
            pass

    data = await _fetch_roles_and_permissions_from_db(db, user_id)
    await r.setex(cache_key, settings.PERMISSION_CACHE_TTL_SECONDS, json.dumps(data))
    return data


async def user_has_permission(db: AsyncSession, r: redis.Redis, user_id: int, permission_code: str) -> bool:
    data = await get_user_roles_and_permissions(db=db, r=r, user_id=user_id)
    return permission_code in set(data["permissions"])


async def assign_role_to_user(db: AsyncSession, r: redis.Redis, user_id: int, role_name: str,) -> UserDB:
    user_stmt = (
        select(UserDB)
        .options(selectinload(UserDB.roles))
        .where(UserDB.id == user_id)
    )
    user_result = await db.execute(user_stmt)
    user = user_result.scalar_one_or_none()
    if user is None:
        raise ValueError("User not found")

    role_stmt = select(RoleDB).where(RoleDB.name == role_name)
    role_result = await db.execute(role_stmt)
    role = role_result.scalar_one_or_none()
    if role is None:
        raise ValueError("Role not found")

    if role not in user.roles:
        user.roles.append(role)
        await db.commit()
        await db.refresh(user)

    await invalidate_user_permissions_cache(user_id=user_id, r=r)
    return user