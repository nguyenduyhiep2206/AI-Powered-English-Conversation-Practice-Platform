from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_permission
from app.core.database import get_db
from app.models.enums import QuizQuestionStatusEnum
from app.models.quiz_passage import QuizPassageDB
from app.models.quiz_question import QuizQuestionDB
from app.schemas.quiz_schema import (
    GenerateQuizRequest,
    GenerateQuizResponse,
    GenerateWritingRequest,
    PublishQuizRequest,
    QuizQuestionListResponse,
    QuizQuestionOut,
)
from app.services.quiz_generation_service import generate_quiz_for_skill
from app.services.skill_graph_service import sync_skills_from_preview
from app.services.writing_generation_service import (
    generate_writing_for_skill,
    writing_publishable,
)

router = APIRouter()


@router.post(
    "/books/{book_id}/sync-skills",
    dependencies=[Depends(require_permission("book:manage"))],
)
@router.post(
    "/books/{book_id}/sync-concepts",
    dependencies=[Depends(require_permission("book:manage"))],
    include_in_schema=False,
)
async def admin_sync_skills(book_id: int, db: AsyncSession = Depends(get_db)):
    """Sync learning skills + book_skill_sources from a ready book's structure preview."""
    try:
        sources, meta = await sync_skills_from_preview(db, book_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return {
        "data": {
            "book_id": book_id,
            "source_count": len(sources),
            "excluded": sum(1 for s in sources if s.is_excluded),
            "llm_used": bool(meta.get("llm_used")),
            "edge_count_added": int(meta.get("edge_count_added") or 0),
            "sources": [
                {
                    "id": s.id,
                    "skill_id": s.skill_id,
                    "unit_id": s.unit_id,
                    "unit_title": s.unit_title,
                    "section_title": s.section_title,
                    "is_excluded": s.is_excluded,
                    "is_primary": s.is_primary,
                }
                for s in sources
            ],
        }
    }


@router.post(
    "/skills/{skill_id}/generate",
    response_model=GenerateQuizResponse,
    dependencies=[Depends(require_permission("book:manage"))],
)
async def admin_generate_quiz(
    skill_id: int,
    body: GenerateQuizRequest,
    db: AsyncSession = Depends(get_db),
):
    try:
        rows = await generate_quiz_for_skill(db, skill_id, count=body.count)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return GenerateQuizResponse(data=[QuizQuestionOut.model_validate(r) for r in rows])


@router.post(
    "/skills/{skill_id}/generate-writing",
    response_model=GenerateQuizResponse,
    dependencies=[Depends(require_permission("book:manage"))],
)
async def admin_generate_writing(
    skill_id: int,
    body: GenerateWritingRequest,
    db: AsyncSession = Depends(get_db),
):
    """Generate draft TOEIC Writing W2/W3 tasks for a skill (W1 needs media upload)."""
    try:
        rows = await generate_writing_for_skill(db, skill_id, count=body.count)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return GenerateQuizResponse(
        data=[QuizQuestionOut.model_validate(r) for r in rows],
        message="Đã tạo writing draft",
    )


@router.get(
    "/books/{book_id}/questions",
    response_model=QuizQuestionListResponse,
    dependencies=[Depends(require_permission("book:manage"))],
)
async def admin_list_questions(
    book_id: int,
    status_filter: QuizQuestionStatusEnum | None = None,
    db: AsyncSession = Depends(get_db),
):
    q = select(QuizQuestionDB).where(QuizQuestionDB.book_id == book_id)
    if status_filter is not None:
        q = q.where(QuizQuestionDB.status == status_filter)
    rows = list((await db.execute(q.order_by(QuizQuestionDB.id.desc()))).scalars().all())
    return QuizQuestionListResponse(data=[QuizQuestionOut.model_validate(r) for r in rows])


@router.post(
    "/questions/publish",
    dependencies=[Depends(require_permission("book:manage"))],
)
async def admin_publish_questions(
    body: PublishQuizRequest,
    db: AsyncSession = Depends(get_db),
):
    if not body.question_ids:
        return {"data": {"published": 0, "skipped": 0, "passages_published": 0}}

    rows = list(
        (
            await db.execute(
                select(QuizQuestionDB).where(QuizQuestionDB.id.in_(body.question_ids))
            )
        )
        .scalars()
        .all()
    )
    published = 0
    skipped = 0
    passage_ids: set[int] = set()
    for row in rows:
        part = row.toeic_part.value if row.toeic_part else None
        if part in {"w1", "w2", "w3"} and not writing_publishable(row):
            skipped += 1
            continue
        row.status = QuizQuestionStatusEnum.published
        published += 1
        if row.passage_id is not None:
            passage_ids.add(int(row.passage_id))

    passages_published = 0
    if passage_ids:
        passages = list(
            (
                await db.execute(
                    select(QuizPassageDB).where(QuizPassageDB.id.in_(passage_ids))
                )
            )
            .scalars()
            .all()
        )
        for passage in passages:
            if passage.status != QuizQuestionStatusEnum.published:
                passage.status = QuizQuestionStatusEnum.published
                passages_published += 1

    await db.commit()
    return {
        "data": {
            "published": published,
            "skipped": skipped,
            "passages_published": passages_published,
        }
    }
