"""Request/response DTOs for AI Tutor sessions."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


class TutorStartSessionRequest(BaseModel):
    roadmap_step_id: int


class TutorMessageDTO(BaseModel):
    id: int
    role: Literal["user", "assistant"]
    content: str
    meta: dict[str, Any] | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class TutorSessionDTO(BaseModel):
    id: int
    user_id: int
    roadmap_step_id: int
    scenario_id: int
    status: Literal["active", "completed", "abandoned"]
    target_skill_ids: list[int]
    message_count: int
    summary: dict[str, Any] | None = None
    started_at: datetime
    ended_at: datetime | None = None
    messages: list[TutorMessageDTO] = Field(default_factory=list)

    model_config = {"from_attributes": True}


class TutorTurnMessageRequest(BaseModel):
    content: str = Field(..., min_length=1)


class TutorTurnMetaDTO(BaseModel):
    correction: dict[str, str] | None = None
    hint: str | None = None
    goal_progress: Literal["none", "partial", "done"] = "none"


class TutorSoftSkillSignalDTO(BaseModel):
    skill_id: int
    signal: str = "needs_practice"
    note: str = ""


class TutorEndSummaryDTO(BaseModel):
    went_well: list[str] = Field(default_factory=list)
    fix_next: list[str] = Field(default_factory=list)
    soft_skill_signals: list[TutorSoftSkillSignalDTO] = Field(default_factory=list)
