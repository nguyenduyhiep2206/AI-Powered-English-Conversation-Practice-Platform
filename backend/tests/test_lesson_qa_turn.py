"""Unit tests for Lesson Q&A turn routing / context."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest
import pytest_asyncio
from sqlalchemy import BigInteger
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.ext.compiler import compiles

import app.models  # noqa: F401 — register metadata
from app.core.database import Base
from app.models.enums import CEFRLevel
from app.models.learning_skill import LearningSkillDB
from app.models.lesson_qa import LessonQaMessageDB, LessonQaSessionDB
from app.models.skill_lesson import SkillLessonDB
from app.models.user import UserDB
from app.services.lesson_qa_service import _build_turn_context, get_or_create_session


@compiles(BigInteger, "sqlite")
def _sqlite_bigint(type_, compiler, **kw):
    return "INTEGER"


@compiles(JSONB, "sqlite")
def _sqlite_jsonb(type_, compiler, **kw):
    return "JSON"


@pytest_asyncio.fixture
async def db_session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    tables = [
        UserDB.__table__,
        LearningSkillDB.__table__,
        SkillLessonDB.__table__,
        LessonQaSessionDB.__table__,
        LessonQaMessageDB.__table__,
    ]
    async with engine.begin() as conn:
        await conn.run_sync(lambda sync_conn: Base.metadata.create_all(sync_conn, tables=tables))

    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        yield session

    await engine.dispose()


@pytest_asyncio.fixture
async def qa_seed(db_session: AsyncSession):
    user = UserDB(username="learner", email="learner@test.com", password_hash="x")
    db_session.add(user)
    await db_session.flush()

    skill = LearningSkillDB(
        slug="reservation-a1",
        title="Making a reservation",
        cefr_level=CEFRLevel.A1,
        skill_type="grammar",
        difficulty_in_level=2,
        is_active=True,
    )
    db_session.add(skill)
    await db_session.commit()
    return {"user": user, "skill": skill}


@pytest.mark.asyncio
async def test_off_topic_skips_retrieve(monkeypatch, db_session, qa_seed):
    retrieve = AsyncMock(return_value=[{"unit_title": "U3", "score": 0.9, "text": "x"}])
    monkeypatch.setattr("app.services.lesson_qa_service.retrieve_for_session", retrieve)
    monkeypatch.setattr("app.services.lesson_qa_service.is_off_topic", lambda _t: True)

    session = await get_or_create_session(
        db_session, qa_seed["user"].id, qa_seed["skill"].id
    )
    ctx = await _build_turn_context(
        db_session,
        session,
        "What is the gold price today?",
        int(qa_seed["skill"].id),
    )

    assert ctx["route"] == "off_topic"
    assert ctx["retrieved_block"] is None
    assert ctx["force_off_topic"] is True
    assert ctx["sources"] == []
    retrieve.assert_not_awaited()


@pytest.mark.asyncio
async def test_question_sets_rag_route(monkeypatch, db_session, qa_seed):
    chunks = [{"unit_title": "U3", "score": 0.9, "text": "A reservation is a booking."}]
    retrieve = AsyncMock(return_value=chunks)
    monkeypatch.setattr("app.services.lesson_qa_service.retrieve_for_session", retrieve)
    monkeypatch.setattr(
        "app.services.lesson_qa_service.resolve_unit_scope",
        AsyncMock(return_value=[]),
    )
    monkeypatch.setattr("app.services.lesson_qa_service.is_off_topic", lambda _t: False)
    monkeypatch.setattr(
        "app.services.lesson_qa_service.cache_get", AsyncMock(return_value=None)
    )
    monkeypatch.setattr("app.services.lesson_qa_service.cache_set", AsyncMock())
    monkeypatch.setattr("app.services.lesson_qa_service.settings.LESSON_QA_RAG_ENABLED", True)

    session = await get_or_create_session(
        db_session, qa_seed["user"].id, qa_seed["skill"].id
    )
    ctx = await _build_turn_context(
        db_session,
        session,
        "What does reservation mean in this lesson?",
        int(qa_seed["skill"].id),
    )

    assert ctx["route"] == "rag"
    assert ctx["retrieved_block"]
    assert ctx["sources"]
    assert ctx["sources"][0]["unit_title"] == "U3"
    assert ctx["force_off_topic"] is False
    retrieve.assert_awaited_once()


@pytest.mark.asyncio
async def test_short_ack_sets_smalltalk_route(monkeypatch, db_session, qa_seed):
    retrieve = AsyncMock(return_value=[{"unit_title": "U3", "score": 0.9, "text": "x"}])
    monkeypatch.setattr("app.services.lesson_qa_service.retrieve_for_session", retrieve)
    monkeypatch.setattr("app.services.lesson_qa_service.is_off_topic", lambda _t: False)
    monkeypatch.setattr("app.services.lesson_qa_service.settings.LESSON_QA_RAG_ENABLED", True)

    session = await get_or_create_session(
        db_session, qa_seed["user"].id, qa_seed["skill"].id
    )
    ctx = await _build_turn_context(
        db_session, session, "thanks", int(qa_seed["skill"].id)
    )

    assert ctx["route"] == "smalltalk"
    assert ctx["retrieved_block"] is None
    assert ctx["sources"] == []
    retrieve.assert_not_awaited()


@pytest.mark.asyncio
async def test_lesson_qa_retrieve_passes_enabled_when_tutor_rag_disabled(
    monkeypatch, db_session, qa_seed
):
    chunks = [{"unit_title": "U3", "score": 0.9, "text": "A reservation is a booking."}]
    retrieve = AsyncMock(return_value=chunks)
    monkeypatch.setattr("app.services.lesson_qa_service.retrieve_for_session", retrieve)
    monkeypatch.setattr(
        "app.services.lesson_qa_service.resolve_unit_scope",
        AsyncMock(return_value=[]),
    )
    monkeypatch.setattr("app.services.lesson_qa_service.is_off_topic", lambda _t: False)
    monkeypatch.setattr(
        "app.services.lesson_qa_service.cache_get", AsyncMock(return_value=None)
    )
    monkeypatch.setattr("app.services.lesson_qa_service.cache_set", AsyncMock())
    monkeypatch.setattr("app.services.lesson_qa_service.settings.TUTOR_RAG_ENABLED", False)
    monkeypatch.setattr("app.services.lesson_qa_service.settings.LESSON_QA_RAG_ENABLED", True)

    session = await get_or_create_session(
        db_session, qa_seed["user"].id, qa_seed["skill"].id
    )
    question = "What does reservation mean in this lesson?"
    ctx = await _build_turn_context(
        db_session,
        session,
        question,
        int(qa_seed["skill"].id),
    )

    assert ctx["route"] == "rag"
    retrieve.assert_awaited_once_with(
        db_session,
        skill_ids=[int(qa_seed["skill"].id)],
        query=question,
        enabled=True,
    )


@pytest.mark.asyncio
async def test_empty_retrieve_sets_retrieval_empty(monkeypatch, db_session, qa_seed):
    retrieve = AsyncMock(return_value=[])
    monkeypatch.setattr("app.services.lesson_qa_service.retrieve_for_session", retrieve)
    monkeypatch.setattr(
        "app.services.lesson_qa_service.resolve_unit_scope",
        AsyncMock(return_value=[]),
    )
    monkeypatch.setattr("app.services.lesson_qa_service.is_off_topic", lambda _t: False)
    monkeypatch.setattr(
        "app.services.lesson_qa_service.cache_get", AsyncMock(return_value=None)
    )
    monkeypatch.setattr("app.services.lesson_qa_service.cache_set", AsyncMock())
    monkeypatch.setattr("app.services.lesson_qa_service.settings.LESSON_QA_RAG_ENABLED", True)

    session = await get_or_create_session(
        db_session, qa_seed["user"].id, qa_seed["skill"].id
    )
    ctx = await _build_turn_context(
        db_session,
        session,
        "What does reservation mean here?",
        int(qa_seed["skill"].id),
    )

    assert ctx["route"] == "retrieval_empty"
    assert ctx["retrieved_block"] is None
    assert ctx["sources"] == []
    retrieve.assert_awaited_once()
