from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_active_user
from app.core.database import get_db
from app.models.learning_skill import LearningSkillDB
from app.models.user import UserDB
from app.services.lesson_service import complete_lesson, get_lesson_for_user, get_published_lesson
from app.services.lesson_writing_feedback import feedback_on_writing

router = APIRouter()


class WritingFeedbackRequest(BaseModel):
    text: str = Field(min_length=1)


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
    _ = current_user
    lesson = await get_published_lesson(db, skill_id)
    if lesson is None:
        raise HTTPException(status_code=404, detail="Published lesson not found")
    skill = (
        await db.execute(select(LearningSkillDB).where(LearningSkillDB.id == skill_id))
    ).scalar_one_or_none()
    cefr = "A1"
    if skill is not None:
        cefr = (
            skill.cefr_level.value
            if hasattr(skill.cefr_level, "value")
            else str(skill.cefr_level)
        )
    content = lesson.content if isinstance(lesson.content, dict) else {}
    writing = content.get("writing") if isinstance(content.get("writing"), dict) else {}
    targets = content.get("targets") if isinstance(content.get("targets"), list) else []
    must_use = writing.get("must_use") if isinstance(writing.get("must_use"), list) else []
    target_surfaces = [
        str(t.get("surface") or "").strip()
        for t in targets
        if isinstance(t, dict) and str(t.get("surface") or "").strip()
    ]
    try:
        return feedback_on_writing(
            learner_text=body.text,
            writing_prompt=str(writing.get("prompt") or ""),
            must_use=[str(x) for x in must_use],
            targets=target_surfaces,
            cefr=cefr,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.post("/{skill_id}/lesson/complete")
async def post_skill_lesson_complete(
    skill_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: UserDB = Depends(get_current_active_user),
):
    try:
        return await complete_lesson(db, int(current_user.id), skill_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
