from typing import Literal, Optional

from pydantic import BaseModel

from app.models.enums import CEFRLevel, GoalEnum, WeakPointEnum


OnboardingStep = Literal["survey", "placement", "completed"]


class OnboardingStatusData(BaseModel):
    survey_done: bool
    placement_done: bool
    onboarding_complete: bool
    current_step: OnboardingStep
    occupation: Optional[str] = None
    goal: Optional[GoalEnum] = None
    weak_point: Optional[WeakPointEnum] = None
    daily_time_min: Optional[int] = None
    current_level: Optional[CEFRLevel] = None
    placement_score: Optional[int] = None


class OnboardingStatusResponse(BaseModel):
    success: bool = True
    data: OnboardingStatusData
