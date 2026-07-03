from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials
from jose import JWTError, jwt
from redis import asyncio as redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.redis import get_redis
from app.core.security import security
from app.models.user import UserDB
from app.schemas.auth_schema import LoginRequest, RefreshRequest, Token
from app.schemas.user_schema import UserCreate
from app.utils.jwt_handler import create_access_token, create_refresh_token
from app.utils.password_hash import get_password_hash
from app.api.deps import get_current_active_user
from app.services.auth_service import authenticate_user, get_user


router = APIRouter()


@router.post("/login", response_model=Token)
async def login(payload: LoginRequest, db: AsyncSession = Depends(get_db), r: redis.Redis = Depends(get_redis)):
    user = await authenticate_user(db, payload.identifier, payload.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    if user.is_active == False:
        raise HTTPException(status_code=400, detail="Inactive user")
    
    access_token = create_access_token(data={"sub": str(user.id)}, expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES))

    refresh_token = create_refresh_token(data={"sub": str(user.id)}, expires_delta=timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS))
    
    redis_key = f"refresh_token:{user.id}"
    
    await r.setex(name=redis_key, time=settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 3600, value=refresh_token)

    return {"access_token": access_token, "refresh_token": refresh_token, "token_type": "bearer"}


@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register(payload: UserCreate, db: AsyncSession = Depends(get_db)):
    user_exist = await get_user(db, payload.username) or await get_user(db, payload.email)

    if user_exist:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Username or email already exists")

    new_user = UserDB(
        username = payload.username,
        email = payload.email,
        password_hash = get_password_hash(payload.password),
        full_name = payload.full_name,
        avatar_url = payload.avatar_url,
        is_active = True,
    )
    try:
        db.add(new_user)
        await db.commit()
        await db.refresh(new_user)
    except Exception:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Failed to register")

    return {"username": new_user.username, "email": new_user.email, "full_name": new_user.full_name, "avatar_url": new_user.avatar_url, "is_active": new_user.is_active}


@router.post("/logout", status_code=status.HTTP_200_OK)
async def logout(current_user: UserDB = Depends(get_current_active_user), credentials: HTTPAuthorizationCredentials = Depends(security), r: redis.Redis = Depends(get_redis)):
    token = credentials.credentials
    try:
        await r.setex(name=f"blocklist:{token}", time=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60, value="logout")
        await r.delete(f"refresh_token:{current_user.id}")
        
        return {"message": "Successfully logged out"}
    except Exception:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")


@router.post("/token/refresh", response_model=Token)
async def refresh_token(body: RefreshRequest, r: redis.Redis = Depends(get_redis)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(body.refresh_token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except JWTError as e:
        raise credentials_exception
    
    stored = await r.get(f"refresh_token:{user_id}")

    if stored is None or stored != body.refresh_token:
        raise credentials_exception
    
    new_access_token = create_access_token(data={"sub": user_id}, expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES))
    
    return {"access_token": new_access_token, "refresh_token": body.refresh_token, "token_type": "bearer"}
