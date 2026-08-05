"""Auth domain: authenticate, register, login/logout/refresh session orchestrators."""

from __future__ import annotations

from fastapi import Request
from redis import asyncio as redis
from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.core.avatar_presets import pick_random_avatar_url
from app.models.auth import RoleDB
from app.models.user import UserDB
from app.schemas.user_schema import UserCreate
from app.services.rbac_service import (
    get_user_roles_and_permissions,
    invalidate_user_permissions_cache,
)
from app.services.refresh_token_service import (
    BrowserSessionConflict,
    RefreshTokenError,
    ensure_browser_session_available,
    issue_session_tokens,
    revoke_refresh_token,
    rotate_refresh_token,
)
from app.utils.password_hash import get_password_hash, verify_password


class AuthError(Exception):
    def __init__(
        self,
        detail: str,
        *,
        status_code: int = 400,
        headers: dict[str, str] | None = None,
    ) -> None:
        super().__init__(detail)
        self.detail = detail
        self.status_code = status_code
        self.headers = headers


async def _get_user_by_id(db: AsyncSession, user_id: int) -> UserDB | None:
    result = await db.execute(
        select(UserDB)
        .options(selectinload(UserDB.roles))
        .where(UserDB.id == user_id)
    )
    return result.scalar_one_or_none()


async def get_user(db: AsyncSession, identifier: str) -> UserDB | None:
    result = await db.execute(
        select(UserDB).where(
            or_(UserDB.username == identifier, UserDB.email == identifier)
        )
    )
    return result.scalar_one_or_none()


async def authenticate_user(
    db: AsyncSession,
    identifier: str,
    password: str,
) -> UserDB | None:
    user = await get_user(db, identifier)
    if user is None or not user.password_hash:
        return None
    if not verify_password(password, user.password_hash):
        return None
    return user


def _require_active_user(user: UserDB | None) -> UserDB:
    if user is None:
        raise AuthError(
            "Incorrect username or password",
            status_code=401,
            headers={"WWW-Authenticate": "Bearer"},
        )
    if user.is_active is False:
        raise AuthError("Inactive user", status_code=400)
    return user


async def _load_learner_role(db: AsyncSession) -> RoleDB | None:
    result = await db.execute(select(RoleDB).where(RoleDB.name == "learner"))
    return result.scalar_one_or_none()


def _build_user_from_register(payload: UserCreate) -> UserDB:
    avatar_url = (payload.avatar_url or "").strip() or pick_random_avatar_url()
    return UserDB(
        username=payload.username,
        email=payload.email,
        password_hash=get_password_hash(payload.password),
        full_name=payload.full_name,
        avatar_url=avatar_url,
        is_active=True,
    )


async def _persist_new_user(
    db: AsyncSession, user: UserDB, learner_role: RoleDB | None
) -> UserDB:
    db.add(user)
    if learner_role is not None:
        user.roles.append(learner_role)
    await db.commit()
    await db.refresh(user)
    return user


async def login_with_password(
    db: AsyncSession,
    *,
    identifier: str,
    password: str,
    remember_me: bool,
    request: Request | None,
    existing_refresh_token: str | None,
) -> dict:
    """Authenticate and issue a browser session (access + refresh)."""
    user = _require_active_user(await authenticate_user(db, identifier, password))
    try:
        await ensure_browser_session_available(db, existing_refresh_token)
    except BrowserSessionConflict as exc:
        raise AuthError(str(exc), status_code=409) from exc

    access_token, refresh_token = await issue_session_tokens(
        db, int(user.id), request, remember_me=remember_me
    )
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "remember_me": bool(remember_me),
    }


async def register_user(db: AsyncSession, payload: UserCreate) -> dict:
    """Create a learner account; does not auto-login."""
    if await get_user(db, payload.username) or await get_user(db, payload.email):
        raise AuthError("Username or email already exists", status_code=400)

    user = _build_user_from_register(payload)
    learner_role = await _load_learner_role(db)
    try:
        saved = await _persist_new_user(db, user, learner_role)
    except IntegrityError as exc:
        await db.rollback()
        raise AuthError("Username or email already exists", status_code=400) from exc
    except SQLAlchemyError as exc:
        await db.rollback()
        raise AuthError("Failed to register", status_code=400) from exc

    return {
        "username": saved.username,
        "email": saved.email,
        "full_name": saved.full_name,
        "avatar_url": saved.avatar_url,
        "is_active": saved.is_active,
    }


async def logout_session(
    db: AsyncSession,
    r: redis.Redis,
    *,
    access_token: str,
    refresh_token: str | None,
) -> None:
    """Blocklist access token and revoke the browser refresh session."""
    await r.setex(
        name=f"blocklist:{access_token}",
        time=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        value="logout",
    )
    if refresh_token:
        await revoke_refresh_token(db, refresh_token)


async def refresh_session(
    db: AsyncSession,
    r: redis.Redis,
    *,
    refresh_token: str | None,
    request: Request | None,
) -> dict:
    """Rotate refresh cookie session and return a new access token."""
    if not refresh_token:
        raise AuthError(
            "Could not validate credentials",
            status_code=401,
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        access_token, new_refresh_token, remember_me, user_id = await rotate_refresh_token(
            db, refresh_token, request
        )
    except RefreshTokenError as exc:
        raise AuthError(
            "Could not validate credentials",
            status_code=401,
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    await invalidate_user_permissions_cache(user_id=user_id, r=r)
    return {
        "access_token": access_token,
        "refresh_token": new_refresh_token,
        "token_type": "bearer",
        "remember_me": remember_me,
    }


async def get_me_payload(
    db: AsyncSession, r: redis.Redis, user: UserDB
) -> dict:
    roles_and_permissions = await get_user_roles_and_permissions(
        db=db, r=r, user_id=int(user.id)
    )
    return {
        "success": True,
        "data": {
            "id": int(user.id),
            "username": user.username,
            "email": user.email,
            "full_name": user.full_name,
            "avatar_url": user.avatar_url,
            "is_active": user.is_active,
            "auth_provider": user.auth_provider,
            "roles": roles_and_permissions["roles"],
            "permissions": roles_and_permissions["permissions"],
        },
    }
