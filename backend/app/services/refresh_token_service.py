from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

from fastapi import Request
from jose import JWTError, jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.auth import RefreshTokenDB
from app.utils.jwt_handler import create_access_token, create_refresh_token


class RefreshTokenError(Exception):
    pass


def _client_meta(request: Request | None) -> tuple[str | None, str | None]:
    if request is None:
        return None, None
    ip_address = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")
    if user_agent and len(user_agent) > 512:
        user_agent = user_agent[:512]
    return ip_address, user_agent


def _decode_refresh_payload(token: str) -> dict:
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    except JWTError as exc:
        raise RefreshTokenError("Invalid refresh token") from exc

    user_id = payload.get("sub")
    jti = payload.get("jti")
    if not user_id or not jti:
        raise RefreshTokenError("Invalid refresh token payload")
    return payload


async def _get_active_token(db: AsyncSession, jti: str) -> RefreshTokenDB | None:
    now = datetime.now(timezone.utc)
    result = await db.execute(
        select(RefreshTokenDB).where(
            RefreshTokenDB.jti == jti,
            RefreshTokenDB.revoked.is_(False),
            RefreshTokenDB.expired_at > now,
        )
    )
    return result.scalar_one_or_none()


def _build_tokens(
    user_id: int, request: Request | None
) -> tuple[str, str, str, datetime, str | None, str | None]:
    ip_address, user_agent = _client_meta(request)
    jti = str(uuid.uuid4())
    refresh_delta = timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)

    access_token = create_access_token(
        data={"sub": str(user_id)},
        expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
    )
    refresh_token, expired_at = create_refresh_token(
        data={"sub": str(user_id)},
        jti=jti,
        expires_delta=refresh_delta,
    )
    return access_token, refresh_token, jti, expired_at, ip_address, user_agent


async def issue_session_tokens(
    db: AsyncSession,
    user_id: int,
    request: Request | None = None,
) -> tuple[str, str]:
    """Create a new auth session without invalidating other active sessions."""
    access_token, refresh_token, jti, expired_at, ip_address, user_agent = _build_tokens(
        user_id, request
    )

    db.add(
        RefreshTokenDB(
            user_id=user_id,
            jti=jti,
            revoked=False,
            ip_address=ip_address,
            user_agent=user_agent,
            expired_at=expired_at,
        )
    )
    await db.commit()

    return access_token, refresh_token


async def rotate_refresh_token(
    db: AsyncSession,
    token: str,
    request: Request | None = None,
) -> tuple[str, str]:
    """Validate the current session refresh token and rotate to a new pair."""
    payload = _decode_refresh_payload(token)
    user_id = int(payload["sub"])
    old_jti = payload["jti"]

    stored = await _get_active_token(db, old_jti)
    if stored is None:
        raise RefreshTokenError("Refresh token revoked or expired")

    stored.revoked = True

    access_token, refresh_token, jti, expired_at, ip_address, user_agent = _build_tokens(
        user_id, request
    )
    db.add(
        RefreshTokenDB(
            user_id=user_id,
            jti=jti,
            revoked=False,
            ip_address=ip_address,
            user_agent=user_agent,
            expired_at=expired_at,
        )
    )
    await db.commit()

    return access_token, refresh_token


async def revoke_refresh_token(db: AsyncSession, token: str) -> None:
    """Revoke only the session identified by this refresh token."""
    try:
        payload = _decode_refresh_payload(token)
    except RefreshTokenError:
        return

    jti = payload["jti"]
    result = await db.execute(select(RefreshTokenDB).where(RefreshTokenDB.jti == jti))
    stored = result.scalar_one_or_none()
    if stored is None:
        return

    stored.revoked = True
    await db.commit()
