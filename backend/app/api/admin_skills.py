from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_permission
from app.core.database import get_db
from app.services.admin_skill_workspace import get_skill_workspace

router = APIRouter()


@router.get(
    "/{skill_id}/workspace",
    dependencies=[Depends(require_permission("book:manage"))],
)
async def admin_skill_workspace(skill_id: int, db: AsyncSession = Depends(get_db)):
    try:
        data = await get_skill_workspace(db, skill_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"data": data}
