from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.profile import UserProfileDB
from app.schemas.onboarding_schema import OnboardingStatusData


async def get_onboarding_status(db: AsyncSession, user_id: int) -> OnboardingStatusData:
    result = await db.execute(
        select(UserProfileDB).where(UserProfileDB.user_id == user_id)
    )
    profile = result.scalar_one_or_none()

    if profile is None:
        return OnboardingStatusData(
            survey_done=False,
            placement_done=False,
            onboarding_complete=False,
            current_step="survey",
        )

    placement_done = profile.placement_score is not None
    onboarding_complete = profile.survey_done and placement_done

    if onboarding_complete:
        current_step = "completed"
    elif profile.survey_done:
        current_step = "placement"
    else:
        current_step = "survey"

    return OnboardingStatusData(
        survey_done=profile.survey_done,
        placement_done=placement_done,
        onboarding_complete=onboarding_complete,
        current_step=current_step,
        occupation=profile.occupation,
        goal=profile.goal,
        weak_point=profile.weak_point,
        daily_time_min=profile.daily_time_min,
        current_level=profile.current_level,
        placement_score=profile.placement_score,
    )
