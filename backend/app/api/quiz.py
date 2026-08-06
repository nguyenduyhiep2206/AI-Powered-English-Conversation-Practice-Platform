from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_active_user
from app.core.database import get_db
from app.models.enums import (
    QuizQuestionStatusEnum,
    QuizQuestionTypeEnum,
    ToeicPartEnum,
)
from app.models.quiz_question import QuizQuestionDB
from app.models.user import UserDB
from app.services.mastery_service import apply_answer
from app.services.quiz_grade import grade_answer

router = APIRouter()


class AnswerRequest(BaseModel):
    question_id: int
    answer: str


class AnswerResponse(BaseModel):
    correct: bool
    mastery: float
    explanation: str | None = None


@router.get("/skills/{skill_id}/questions")
async def list_published_questions(
    skill_id: int,
    limit: int = Query(default=5, ge=1, le=20),
    db: AsyncSession = Depends(get_db),
    current_user: UserDB = Depends(get_current_active_user),
):
    """Return published questions for a skill — never leak the answer field."""
    base_filters = (
        QuizQuestionDB.skill_id == skill_id,
        QuizQuestionDB.status == QuizQuestionStatusEnum.published,
        QuizQuestionDB.question_type != QuizQuestionTypeEnum.writing,
        (QuizQuestionDB.toeic_part.is_(None))
        | (
            QuizQuestionDB.toeic_part.notin_(
                [ToeicPartEnum.w1, ToeicPartEnum.w2, ToeicPartEnum.w3]
            )
        ),
    )
    skill_drill_mode = QuizQuestionDB.task_brief["mode"].as_string() == "skill_drill"
    skill_drill_count = int(
        (
            await db.execute(
                select(func.count())
                .select_from(QuizQuestionDB)
                .where(*base_filters, skill_drill_mode)
            )
        ).scalar_one()
    )

    q = select(QuizQuestionDB).where(*base_filters)
    if skill_drill_count >= limit:
        q = q.where(skill_drill_mode)

    q = q.order_by(func.random()).limit(limit)
    rows = list((await db.execute(q)).scalars().all())
    return {
        "data": [
            {
                "id": r.id,
                "skill_id": r.skill_id,
                "question_type": r.question_type.value
                if hasattr(r.question_type, "value")
                else r.question_type,
                "stem": r.stem,
                "passage": r.passage,
                "toeic_part": r.toeic_part.value
                if getattr(r, "toeic_part", None) and hasattr(r.toeic_part, "value")
                else (r.toeic_part if getattr(r, "toeic_part", None) else None),
                "options": r.options,
                "difficulty": r.difficulty,
                "item_kind": (r.task_brief or {}).get("item_kind")
                if isinstance(r.task_brief, dict)
                else None,
            }
            for r in rows
        ]
    }


@router.post("/answer", response_model=AnswerResponse)
async def submit_answer(
    body: AnswerRequest,
    db: AsyncSession = Depends(get_db),
    current_user: UserDB = Depends(get_current_active_user),
):
    question = (
        await db.execute(select(QuizQuestionDB).where(QuizQuestionDB.id == body.question_id))
    ).scalar_one_or_none()
    if question is None or question.status != QuizQuestionStatusEnum.published:
        raise HTTPException(status_code=404, detail="Không tìm thấy câu hỏi")

    question_type = (
        question.question_type.value
        if hasattr(question.question_type, "value")
        else question.question_type
    )
    correct = grade_answer(question_type, question.answer, body.answer)
    mastery_row = await apply_answer(
        db,
        int(current_user.id),
        int(question.skill_id),
        correct,
    )
    return AnswerResponse(
        correct=correct,
        mastery=float(mastery_row.mastery),
        explanation=question.explanation,
    )
