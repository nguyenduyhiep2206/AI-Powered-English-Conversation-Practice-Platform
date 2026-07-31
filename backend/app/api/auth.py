from typing import Optional

from fastapi import APIRouter, Cookie, Depends, HTTPException, Request, Response, status
from fastapi.security import HTTPAuthorizationCredentials
from redis import asyncio as redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_active_user
from app.core.database import get_db
from app.core.redis import get_redis
from app.core.security import security
from app.models.user import UserDB
from app.schemas.auth_schema import LoginRequest, MeResponse, Token
from app.schemas.user_schema import UserCreate
from app.services.auth_service import (
    AuthError,
    get_me_payload,
    login_with_password,
    logout_session,
    refresh_session,
    register_user,
)
from app.utils.auth_cookies import clear_refresh_token_cookie, set_refresh_token_cookie

router = APIRouter()


def _http_error(exc: AuthError) -> HTTPException:
    return HTTPException(
        status_code=exc.status_code,
        detail=exc.detail,
        headers=exc.headers,
    )


@router.post("/login", response_model=Token)
async def login(
    request: Request,
    response: Response,
    payload: LoginRequest,
    db: AsyncSession = Depends(get_db),
    existing_refresh_token: Optional[str] = Cookie(None, alias="refresh_token"),
):
    try:
        result = await login_with_password(
            db,
            identifier=payload.identifier,
            password=payload.password,
            remember_me=bool(payload.remember_me),
            request=request,
            existing_refresh_token=existing_refresh_token,
        )
    except AuthError as exc:
        raise _http_error(exc) from exc

    set_refresh_token_cookie(
        response, result["refresh_token"], remember_me=result["remember_me"]
    )
    return {
        "access_token": result["access_token"],
        "token_type": result["token_type"],
        "remember_me": result["remember_me"],
    }


@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register(payload: UserCreate, db: AsyncSession = Depends(get_db)):
    try:
        return await register_user(db, payload)
    except AuthError as exc:
        raise _http_error(exc) from exc


@router.post("/logout", status_code=status.HTTP_200_OK)
async def logout(
    response: Response,
    current_user: UserDB = Depends(get_current_active_user),
    credentials: HTTPAuthorizationCredentials = Depends(security),
    r: redis.Redis = Depends(get_redis),
    db: AsyncSession = Depends(get_db),
    refresh_token: Optional[str] = Cookie(None, alias="refresh_token"),
):
    try:
        await logout_session(
            db,
            r,
            access_token=credentials.credentials,
            refresh_token=refresh_token,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        ) from exc
    clear_refresh_token_cookie(response)
    return {"message": "Successfully logged out"}


@router.get("/me", response_model=MeResponse, status_code=status.HTTP_200_OK)
async def me(
    current_user: UserDB = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
    r: redis.Redis = Depends(get_redis),
):
    return await get_me_payload(db, r, current_user)


@router.post("/token/refresh", response_model=Token)
async def refresh_token(
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
    r: redis.Redis = Depends(get_redis),
    token: Optional[str] = Cookie(None, alias="refresh_token"),
):
    try:
        result = await refresh_session(
            db, r, refresh_token=token, request=request
        )
    except AuthError as exc:
        raise _http_error(exc) from exc

    set_refresh_token_cookie(
        response, result["refresh_token"], remember_me=result["remember_me"]
    )
    return {
        "access_token": result["access_token"],
        "token_type": result["token_type"],
        "remember_me": result["remember_me"],
    }
