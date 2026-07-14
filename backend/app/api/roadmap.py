from pydantic import BaseModel, Field

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_active_user
from app.core.database import get_db
from app.models.enums import CEFRLevel
from app.models.user import UserDB
from app.services.roadmap_assembler_service import assemble_user_roadmap

router = APIRouter()


class AssembleRequest(BaseModel):
    level: CEFRLevel | None = None
    max_steps: int = Field(default=10, ge=8, le=12)


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
