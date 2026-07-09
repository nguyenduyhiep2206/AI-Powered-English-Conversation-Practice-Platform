from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_permission
from app.core.database import get_db
from app.schemas.survey_schema import (
    SurveyQuestionAdmin,
    SurveyQuestionCreate,
    SurveyQuestionListResponse,
    SurveyQuestionResponse,
    SurveyQuestionUpdate,
)
from app.services.survey_service import (
    create_survey_question,
    deactivate_survey_question,
    list_all_survey_questions,
    update_survey_question,
)

router = APIRouter()


def _to_admin(question) -> SurveyQuestionAdmin:
    return SurveyQuestionAdmin.model_validate(question)


@router.get(
    "/questions",
    response_model=SurveyQuestionListResponse,
    dependencies=[Depends(require_permission("scenario:edit"))],
)
async def admin_list_survey_questions(db: AsyncSession = Depends(get_db)):
    questions = await list_all_survey_questions(db)
    return SurveyQuestionListResponse(data=[_to_admin(q) for q in questions])


@router.post(
    "/questions",
    response_model=SurveyQuestionResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("scenario:edit"))],
)
async def admin_create_survey_question(
    payload: SurveyQuestionCreate,
    db: AsyncSession = Depends(get_db),
):
    question = await create_survey_question(db, payload)
    return SurveyQuestionResponse(data=_to_admin(question))


@router.put(
    "/questions/{question_id}",
    response_model=SurveyQuestionResponse,
    dependencies=[Depends(require_permission("scenario:edit"))],
)
async def admin_update_survey_question(
    question_id: int,
    payload: SurveyQuestionUpdate,
    db: AsyncSession = Depends(get_db),
):
    question = await update_survey_question(db, question_id, payload)
    return SurveyQuestionResponse(data=_to_admin(question))


@router.delete(
    "/questions/{question_id}",
    response_model=SurveyQuestionResponse,
    dependencies=[Depends(require_permission("scenario:edit"))],
)
async def admin_delete_survey_question(
    question_id: int,
    db: AsyncSession = Depends(get_db),
):
    question = await deactivate_survey_question(db, question_id)
    return SurveyQuestionResponse(data=_to_admin(question))
