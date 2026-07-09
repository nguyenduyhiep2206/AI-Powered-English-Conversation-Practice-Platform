import logging

from typing import Optional

from fastapi import APIRouter, Cookie, Depends, HTTPException, Request, Response, status
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.concurrency import run_in_threadpool

from app.core.config import settings
from app.core.database import get_db
from app.models.user import UserDB
from app.schemas.auth_schema import GoogleLoginRequest, Token
from app.services.refresh_token_service import ensure_browser_session_available, issue_session_tokens
from app.utils.auth_cookies import set_refresh_token_cookie

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/google", response_model=Token)
async def google_login(
    request: Request,
    response: Response,
    payload: GoogleLoginRequest,
    db: AsyncSession = Depends(get_db),
    existing_refresh_token: Optional[str] = Cookie(None, alias="refresh_token"),
):
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

    await ensure_browser_session_available(db, existing_refresh_token)

    access_token, refresh_token = await issue_session_tokens(db, int(user.id), request)
    set_refresh_token_cookie(response, refresh_token)

    return {
        "access_token": access_token,
        "token_type": "bearer",
    }
