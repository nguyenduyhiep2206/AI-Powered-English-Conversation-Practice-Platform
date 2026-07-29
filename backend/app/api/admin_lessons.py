from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_permission
from app.core.database import get_db
from app.services.lesson_generation_service import generate_lesson_draft, lesson_to_dict, publish_lesson
from app.services.lesson_service import get_admin_lesson, list_skills_with_lesson_status

router = APIRouter()


@router.get(
    "/skills",
    dependencies=[Depends(require_permission("book:manage"))],
)
async def admin_list_skills_for_lessons(
    cefr_level: str | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
):
    rows = await list_skills_with_lesson_status(db, cefr_level=cefr_level)
    return {"data": rows}


@router.get(
    "/skills/{skill_id}",
    dependencies=[Depends(require_permission("book:manage"))],
)
async def admin_get_lesson(skill_id: int, db: AsyncSession = Depends(get_db)):
    try:
        return {"data": await get_admin_lesson(db, skill_id)}
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post(
    "/skills/{skill_id}/generate",
    dependencies=[Depends(require_permission("book:manage"))],
)
async def admin_generate_lesson(skill_id: int, db: AsyncSession = Depends(get_db)):
    try:
        lesson = await generate_lesson_draft(db, skill_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return {"data": lesson_to_dict(lesson)}


@router.post(
    "/skills/{skill_id}/publish",
    dependencies=[Depends(require_permission("book:manage"))],
)
async def admin_publish_lesson(skill_id: int, db: AsyncSession = Depends(get_db)):
    try:
        lesson = await publish_lesson(db, skill_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"data": lesson_to_dict(lesson)}
