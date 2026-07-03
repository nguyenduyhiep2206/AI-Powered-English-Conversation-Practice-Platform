from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests
from datetime import timedelta
from redis import asyncio as redis
from starlette.concurrency import run_in_threadpool
import logging
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import settings
from app.core.database import get_db
from app.core.redis import get_redis
from app.utils.jwt_handler import create_access_token, create_refresh_token
from app.models.user import UserDB
from app.schemas.auth_schema import GoogleLoginRequest, Token

logger = logging.getLogger(__name__)
router = APIRouter()

@router.post("/google", response_model=Token)
async def google_login( payload: GoogleLoginRequest, db: AsyncSession = Depends(get_db), r: redis.Redis = Depends(get_redis)):
    # Verify token with Google -> ensure the token is genuine and not tampered with
    try:
        idinfo = await run_in_threadpool(
            id_token.verify_oauth2_token,
            payload.credential,
            google_requests.Request(),
            settings.GOOGLE_CLIENT_ID,
        )
    except Exception as e:
        logger.error(f"Google token verification failed: {type(e).__name__}: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid Google token: {str(e)}",
        )

    email = idinfo.get("email")
    name = idinfo.get("name")
    email_verified = idinfo.get("email_verified", False)

    if not email or not email_verified:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Google email not verified",
        )

    # Find user by email, if not found, create a new one (auto-register)
    result = await db.execute(select(UserDB).where(UserDB.email == email))
    user = result.scalar_one_or_none()

    if not user:
        user = UserDB(
            email=email,
            username=email.split("@")[0],
            full_name=name,
            is_active=True,
            password_hash=None,
            auth_provider="google",
        )
        try:
            db.add(user)
            await db.commit()
            await db.refresh(user)
        except Exception:
            await db.rollback()
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Failed to register")

    if not user.is_active:
        raise HTTPException(status_code=400, detail="Account is locked")

    # Issue system JWT — same as regular login flow
    access_token = create_access_token(
        data={"sub": str(user.id)},
        expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
    )
    refresh_token = create_refresh_token(
        data={"sub": str(user.id)},
        expires_delta=timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
    )

    await r.setex(
        f"refresh_token:{user.id}",
        settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 3600,
        refresh_token,
    )

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
    }