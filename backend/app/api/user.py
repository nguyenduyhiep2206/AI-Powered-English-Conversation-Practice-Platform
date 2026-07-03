from sqlalchemy import select
from app.core.database import get_db
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.user import UserDB
from fastapi import APIRouter, Depends, HTTPException, status
from app.schemas.user_schema import User, UpdateUser, UserResponse
from app.api.auth import get_current_active_user


router = APIRouter()


@router.get("/users/me", response_model=UserResponse)
async def read_user_me(current_user: UserDB = Depends(get_current_active_user)):
    return current_user


@router.get("/users/all", response_model=list[UserResponse])
async def read_all_user(db: AsyncSession = Depends(get_db), current_user: UserDB = Depends(get_current_active_user)):
    result = await db.execute(select(UserDB))
    users = result.scalars().all()
    return users
    
    
@router.put("/users/me", response_model=UserResponse)
async def update_user_me(updated_user: UpdateUser, db: AsyncSession = Depends(get_db), current_user: UserDB = Depends(get_current_active_user)):
    credential_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if not current_user:
        raise credential_exception
    result = await db.execute(select(UserDB).where(UserDB.username == current_user.username))
    user = result.scalar_one_or_none()
    if not user:
        raise credential_exception
    
    if updated_user.username is not None:
        user.username = updated_user.username
    if updated_user.full_name is not None:
        user.full_name = updated_user.full_name
    if updated_user.avatar_url is not None:
        user.avatar_url = updated_user.avatar_url
    if updated_user.is_active is not None:
        user.is_active = updated_user.is_active
    if updated_user.updated_at is not None:
        user.updated_at = updated_user.updated_at
    await db.commit()
    await db.refresh(user)
    return user