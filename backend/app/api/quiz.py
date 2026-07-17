from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_active_user
from app.core.database import get_db
from app.models.enums import QuizQuestionStatusEnum
from app.models.quiz_question import QuizQuestionDB
from app.models.user import UserDB
from app.services.mastery_service import apply_answer, grade_mcq

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
    q = (
        select(QuizQuestionDB)
        .where(
            QuizQuestionDB.skill_id == skill_id,
            QuizQuestionDB.status == QuizQuestionStatusEnum.published,
        )
        .order_by(func.random())
        .limit(limit)
    )
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
                "options": r.options,
                "difficulty": r.difficulty,
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

    correct = grade_mcq(question.answer, body.answer)
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
