from pydantic import BaseModel, Field

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_active_user
from app.core.database import get_db
from app.models.enums import CEFRLevel
from app.models.user import UserDB
from app.services.roadmap_assembler_service import (
    assemble_user_roadmap,
    get_user_roadmap,
)
from app.services.roadmap_progress_service import complete_roadmap_week

router = APIRouter()


class AssembleRequest(BaseModel):
    level: CEFRLevel | None = None
    max_steps: int = Field(default=30, ge=1, le=40)


@router.get("")
async def get_roadmap(
    db: AsyncSession = Depends(get_db),
    current_user: UserDB = Depends(get_current_active_user),
):
    data = await get_user_roadmap(db, int(current_user.id))
    return {"data": data}


@router.post("/assemble")
async def assemble_roadmap(
    body: AssembleRequest,
    db: AsyncSession = Depends(get_db),
    current_user: UserDB = Depends(get_current_active_user),
):
    try:
        data = await assemble_user_roadmap(
            db,
            int(current_user.id),
            level=body.level,
            max_steps=body.max_steps,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"data": data}


@router.post("/steps/{roadmap_step_id}/complete")
async def complete_step(
    roadmap_step_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: UserDB = Depends(get_current_active_user),
):
    try:
        data = await complete_roadmap_week(
            db,
            int(current_user.id),
            int(roadmap_step_id),
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"data": data}
