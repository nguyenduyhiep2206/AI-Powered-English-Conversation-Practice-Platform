from sqlalchemy import or_, select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import UserDB
from app.utils.password_hash import verify_password


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