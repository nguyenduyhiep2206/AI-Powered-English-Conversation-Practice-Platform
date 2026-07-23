from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field

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


class PlacementAnswerIn(BaseModel):
    question_id: int
    answer: str


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


class LevelChallengeQuestionsData(BaseModel):
    target_level: str
    question_count: int
    questions: list[PlacementQuestionOut]


class LevelChallengeQuestionsResponse(BaseModel):
    success: bool = True
    data: LevelChallengeQuestionsData


class LevelChallengeSubmitRequest(BaseModel):
    target_level: CEFRLevel
    answers: list[PlacementAnswerIn] = Field(min_length=6, max_length=6)


class LevelChallengeResultData(BaseModel):
    passed: bool
    correct_count: int
    total: int
    current_level: str
    placement_score: int | None = None
    target_level: str


class LevelChallengeSubmitResponse(BaseModel):
    success: bool = True
    data: LevelChallengeResultData
