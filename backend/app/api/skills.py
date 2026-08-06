from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_active_user
from app.core.database import get_db
from app.models.user import UserDB
from app.services.lesson_service import (
    complete_lesson,
    get_lesson_for_user,
    writing_feedback_for_skill,
)

router = APIRouter()


class WritingFeedbackRequest(BaseModel):
    text: str = Field(min_length=1)
    pack_index: int | None = None


@router.get("/{skill_id}/lesson")
async def get_skill_lesson(
    skill_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: UserDB = Depends(get_current_active_user),
):
    try:
        return await get_lesson_for_user(db, int(current_user.id), skill_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/{skill_id}/lesson/writing/feedback")
async def post_skill_lesson_writing_feedback(
    skill_id: int,
    body: WritingFeedbackRequest,
    db: AsyncSession = Depends(get_db),
    current_user: UserDB = Depends(get_current_active_user),
):
    _ = current_user  # auth gate; feedback is skill-scoped, not user-personalized
    try:
        return await writing_feedback_for_skill(
            db,
            skill_id,
            text=body.text,
            pack_index=body.pack_index,
        )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.post("/{skill_id}/lesson/complete")
async def post_skill_lesson_complete(
    skill_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: UserDB = Depends(get_current_active_user),
    pack_index: int = Query(default=0, ge=0, le=10),
):
    try:
        return await complete_lesson(
            db, int(current_user.id), skill_id, pack_index=pack_index
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
