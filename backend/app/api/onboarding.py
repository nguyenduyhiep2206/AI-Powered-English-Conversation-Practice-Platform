from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_active_user, require_permission
from app.core.database import get_db
from app.models.user import UserDB
from app.schemas.onboarding_schema import OnboardingStatusResponse
from app.schemas.survey_schema import (
    SubmitSurveyRequest,
    SubmitSurveyResponse,
    SubmitSurveyData,
    SurveyQuestionsData,
    SurveyQuestionsResponse,
)
from app.services.onboarding_service import get_onboarding_status
from app.services.survey_service import get_survey_questions_for_user, submit_survey

router = APIRouter()


@router.get("/status", response_model=OnboardingStatusResponse)
async def onboarding_status(
    current_user: UserDB = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Check whether the user has completed survey and placement test."""
    data = await get_onboarding_status(db, int(current_user.id))
    return OnboardingStatusResponse(data=data)


@router.get("/survey/questions", response_model=SurveyQuestionsResponse)
async def survey_questions(
    current_user: UserDB = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    questions = await get_survey_questions_for_user(db, int(current_user.id))
    return SurveyQuestionsResponse(data=SurveyQuestionsData(questions=questions))


@router.post("/survey", response_model=SubmitSurveyResponse, status_code=200)
async def submit_survey_answers(
    payload: SubmitSurveyRequest,
    current_user: UserDB = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    await submit_survey(db, int(current_user.id), payload.answers)
    return SubmitSurveyResponse(data=SubmitSurveyData())
