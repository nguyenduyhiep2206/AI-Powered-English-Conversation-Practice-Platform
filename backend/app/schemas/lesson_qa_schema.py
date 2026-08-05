"""Request/response DTOs for Lesson Q&A chatbot."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class LessonQaMessageDTO(BaseModel):
    id: int
    role: str
    content: str
    meta: dict[str, Any] | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class LessonQaSessionDTO(BaseModel):
    id: int
    skill_id: int
    status: str
    message_count: int

    model_config = {"from_attributes": True}


class LessonQaBundleDTO(BaseModel):
    session: LessonQaSessionDTO
    messages: list[LessonQaMessageDTO]
    suggested_prompts: list[str]


class LessonQaTurnRequest(BaseModel):
    content: str = Field(..., min_length=1, max_length=2000)
    debug: bool = False
