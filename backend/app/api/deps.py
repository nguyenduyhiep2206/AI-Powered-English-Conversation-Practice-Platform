from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials
from jose import JWTError, jwt
from redis import asyncio as redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.redis import get_redis
from app.core.security import security
from app.models.user import UserDB
from app.schemas.auth_schema import Token_data
from app.services.auth_service import _get_user_by_id
from app.services.rbac_service import user_has_permission

def _build_credentials_exception() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
    r: redis.Redis = Depends(get_redis),
) -> UserDB:
    token = credentials.credentials
    credentials_exception = _build_credentials_exception()

    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception

        if await r.get(name=f"blocklist:{token}"):
            raise credentials_exception

        token_data = Token_data(user_id=user_id)
    except JWTError:
        raise credentials_exception

    try:
        user_id_int = int(token_data.user_id)
    except (TypeError, ValueError):
        raise credentials_exception

    user = await _get_user_by_id(db, user_id_int)
    if user is None:
        raise credentials_exception

    return user


def get_current_active_user(
    current_user: UserDB = Depends(get_current_user),
) -> UserDB:
    if not current_user.is_active:
        raise HTTPException(status_code=403, detail="Inactive user")

    return current_user


class RoleChecker:
    def __init__(self, allowed_roles: list[str]):
        self.allowed_roles = set(allowed_roles)

    @staticmethod
    def _get_role_names(current_user: UserDB) -> set[str]:
        return {role.name for role in current_user.roles}

    def __call__(self, current_user: UserDB = Depends(get_current_user)) -> UserDB:
        user_roles = self._get_role_names(current_user)
        if user_roles.intersection(self.allowed_roles):
            return current_user

        raise HTTPException(status_code=403, detail="Operation not permitted")


def require_permission(code: str):
    async def permission_dependency(
        current_user: UserDB = Depends(get_current_active_user),
        db: AsyncSession = Depends(get_db),
        r: redis.Redis = Depends(get_redis),
    ) -> UserDB:
        is_allowed = await user_has_permission(
            db=db,
            r=r,
            user_id=int(current_user.id),
            permission_code=code,
        )
        if not is_allowed:
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        return current_user

    return permission_dependency