from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_active_user
from app.core.database import get_db
from app.models.user import UserDB
from app.schemas.onboarding_schema import (
    OnboardingStatusResponse,
    PlacementQuestionOut,
    PlacementQuestionsData,
    PlacementQuestionsResponse,
    PlacementResultData,
    PlacementSubmitRequest,
    PlacementSubmitResponse,
)
from app.schemas.survey_schema import (
    SubmitSurveyData,
    SubmitSurveyRequest,
    SubmitSurveyResponse,
    SurveyQuestionsData,
    SurveyQuestionsResponse,
)
from app.services.onboarding_service import get_onboarding_status
from app.services.placement_service import (
    INSUFFICIENT_BANK_MSG,
    get_placement_questions_for_user,
    placement_public_dict,
    submit_placement,
)
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


@router.get("/questions", response_model=PlacementQuestionsResponse)
async def placement_questions(
    current_user: UserDB = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Return 10 published placement questions (no answers)."""
    try:
        picked = await get_placement_questions_for_user(db, int(current_user.id))
    except PermissionError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except ValueError as exc:
        status = 503 if str(exc) == INSUFFICIENT_BANK_MSG else 400
        raise HTTPException(status_code=status, detail=str(exc)) from exc

    questions = [PlacementQuestionOut(**placement_public_dict(c)) for c in picked]
    return PlacementQuestionsResponse(
        data=PlacementQuestionsData(question_count=len(questions), questions=questions)
    )


@router.post("/placement", response_model=PlacementSubmitResponse)
async def placement_submit(
    payload: PlacementSubmitRequest,
    current_user: UserDB = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Grade placement answers, set CEFR level and mastery. Does not assemble roadmap."""
    try:
        result = await submit_placement(
            db,
            int(current_user.id),
            [a.model_dump() for a in payload.answers],
        )
    except PermissionError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return PlacementSubmitResponse(data=PlacementResultData(**result))
