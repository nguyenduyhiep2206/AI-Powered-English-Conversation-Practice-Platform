from sqlalchemy import select
from app.core.database import get_db
from app.core.redis import get_redis
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.user import UserDB
from redis import asyncio as redis
from fastapi import APIRouter, Depends, HTTPException, status
from app.schemas.user_schema import User, UpdateUser, UserResponse
from app.api.deps import get_current_active_user, require_permission
from app.services.rbac_service import assign_role_to_user


router = APIRouter()


@router.get("/users/me", response_model=UserResponse)
async def read_user_me(current_user: UserDB = Depends(get_current_active_user)):
    return current_user


@router.get("/users/all", response_model=list[UserResponse], dependencies=[Depends(require_permission("report:view_all"))])
async def read_all_user(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(UserDB))
    users = result.scalars().all()
    return users


@router.post("/users/{user_id}/roles/{role_name}", dependencies=[Depends(require_permission("report:view_all"))],)
async def assign_user_role(user_id: int, role_name: str, db: AsyncSession = Depends(get_db), r: redis.Redis = Depends(get_redis)):
    try:
        await assign_role_to_user(db=db, r=r, user_id=user_id, role_name=role_name)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))

    return {
        "success": True,
        "data": {
            "user_id": user_id,
            "role_name": role_name,
            "message": "Role assigned and permission cache invalidated",
        },
    }
    
    
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