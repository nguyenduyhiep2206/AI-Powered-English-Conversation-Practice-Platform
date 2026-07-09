from typing import Optional

from fastapi import APIRouter, Cookie, Depends, HTTPException, Request, Response, status
from fastapi.security import HTTPAuthorizationCredentials
from jose import JWTError, jwt
from redis import asyncio as redis
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_active_user
from app.core.config import settings
from app.core.database import get_db
from app.core.redis import get_redis
from app.core.security import security
from app.models.auth import RoleDB
from app.models.user import UserDB
from app.schemas.auth_schema import LoginRequest, MeResponse, Token
from app.schemas.user_schema import UserCreate
from app.services.auth_service import authenticate_user, get_user
from app.services.rbac_service import get_user_roles_and_permissions, invalidate_user_permissions_cache
from app.services.refresh_token_service import RefreshTokenError, issue_session_tokens, revoke_refresh_token, rotate_refresh_token
from app.utils.auth_cookies import clear_refresh_token_cookie, set_refresh_token_cookie
from app.utils.password_hash import get_password_hash

router = APIRouter()


@router.post("/login", response_model=Token)
async def login(
    request: Request,
    response: Response,
    payload: LoginRequest,
    db: AsyncSession = Depends(get_db),
):
    user = await authenticate_user(db, payload.identifier, payload.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if user.is_active is False:
        raise HTTPException(status_code=400, detail="Inactive user")

    access_token, refresh_token = await issue_session_tokens(db, int(user.id), request)
    set_refresh_token_cookie(response, refresh_token)

    return {"access_token": access_token, "token_type": "bearer"}


@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register(payload: UserCreate, db: AsyncSession = Depends(get_db)):
    user_exist = await get_user(db, payload.username) or await get_user(db, payload.email)

    if user_exist:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Username or email already exists")

    new_user = UserDB(
        username=payload.username,
        email=payload.email,
        password_hash=get_password_hash(payload.password),
        full_name=payload.full_name,
        avatar_url=payload.avatar_url,
        is_active=True,
    )
    try:
        learner_result = await db.execute(select(RoleDB).where(RoleDB.name == "learner"))
        learner_role = learner_result.scalar_one_or_none()

        db.add(new_user)
        if learner_role is not None:
            new_user.roles.append(learner_role)

        await db.commit()
        await db.refresh(new_user)
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Username or email already exists")
    except SQLAlchemyError:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Failed to register")

    return {
        "username": new_user.username,
        "email": new_user.email,
        "full_name": new_user.full_name,
        "avatar_url": new_user.avatar_url,
        "is_active": new_user.is_active,
    }


@router.post("/logout", status_code=status.HTTP_200_OK)
async def logout(
    response: Response,
    current_user: UserDB = Depends(get_current_active_user),
    credentials: HTTPAuthorizationCredentials = Depends(security),
    r: redis.Redis = Depends(get_redis),
    db: AsyncSession = Depends(get_db),
    refresh_token: Optional[str] = Cookie(None, alias="refresh_token"),
):
    token = credentials.credentials
    try:
        await r.setex(
            name=f"blocklist:{token}",
            time=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            value="logout",
        )
        if refresh_token:
            await revoke_refresh_token(db, refresh_token)
        clear_refresh_token_cookie(response)
        return {"message": "Successfully logged out"}
    except Exception:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")


@router.get("/me", response_model=MeResponse, status_code=status.HTTP_200_OK)
async def me(
    current_user: UserDB = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
    r: redis.Redis = Depends(get_redis),
):
    roles_and_permissions = await get_user_roles_and_permissions(
        db=db,
        r=r,
        user_id=int(current_user.id),
    )
    return {
        "success": True,
        "data": {
            "id": int(current_user.id),
            "username": current_user.username,
            "email": current_user.email,
            "full_name": current_user.full_name,
            "avatar_url": current_user.avatar_url,
            "is_active": current_user.is_active,
            "auth_provider": current_user.auth_provider,
            "roles": roles_and_permissions["roles"],
            "permissions": roles_and_permissions["permissions"],
        },
    }


@router.post("/token/refresh", response_model=Token)
async def refresh_token(
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
    r: redis.Redis = Depends(get_redis),
    token: Optional[str] = Cookie(None, alias="refresh_token"),
):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if token is None:
        raise credentials_exception

    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id = int(payload["sub"])
        access_token, new_refresh_token = await rotate_refresh_token(db, token, request)
    except RefreshTokenError:
        raise credentials_exception
    except (JWTError, TypeError, ValueError):
        raise credentials_exception

    await invalidate_user_permissions_cache(user_id=user_id, r=r)
    set_refresh_token_cookie(response, new_refresh_token)

    return {"access_token": access_token, "token_type": "bearer"}
