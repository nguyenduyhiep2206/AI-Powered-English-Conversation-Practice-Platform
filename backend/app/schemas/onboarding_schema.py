from datetime import datetime
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


class PlacementQuestionOut(BaseModel):
    id: int
    skill_id: int
    cefr_level: str
    question_type: str
    stem: str
    passage: str | None = None
    options: list[str] | None = None
    difficulty: str


class PlacementProgressOut(BaseModel):
    asked: int
    min_questions: int = 6
    max_questions: int = 15


class PlacementSessionData(BaseModel):
    done: bool
    attempt_id: int
    question: PlacementQuestionOut | None = None
    progress: PlacementProgressOut | None = None
    placement_score: int | None = None
    current_level: str | None = None
    questions_asked: int | None = None
    onboarding_complete: bool | None = None


class PlacementSessionResponse(BaseModel):
    success: bool = True
    data: PlacementSessionData


class PlacementAnswerRequest(BaseModel):
    question_id: int
    answer: str


class PlacementRetakeStatusData(BaseModel):
    allowed: bool
    has_in_progress: bool
    retry_after_at: datetime | None = None


class PlacementRetakeStatusResponse(BaseModel):
    success: bool = True
    data: PlacementRetakeStatusData
