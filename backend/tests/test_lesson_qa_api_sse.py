"""API tests for Lesson Q&A SSE message streaming."""

from __future__ import annotations

from collections.abc import AsyncIterator

import pytest
import pytest_asyncio
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import BigInteger
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.ext.compiler import compiles

import app.models  # noqa: F401
from app.api import lesson_qa
from app.api.deps import get_current_active_user
from app.core.database import Base, get_db
from app.models.enums import CEFRLevel
from app.models.learning_skill import LearningSkillDB
from app.models.lesson_qa import LessonQaMessageDB, LessonQaSessionDB
from app.models.skill_lesson import SkillLessonDB
from app.models.user import UserDB


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
async def api_client(db_session: AsyncSession):
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

    app = FastAPI()
    app.include_router(lesson_qa.router, prefix="/api/v1/lessons")

    async def override_get_db():
        yield db_session

    async def override_current_user():
        return user

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_active_user] = override_current_user

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client, skill

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_post_message_streams_token_meta_done(api_client, monkeypatch):
    client, skill = api_client

    async def fake_iter_qa_turn_sse(
        _db, _user_id, _skill_id, _content, *, debug: bool = False
    ) -> AsyncIterator[tuple[str, dict]]:
        yield ("token", {"text": "A reservation "})
        yield ("token", {"text": "is a booking."})
        yield ("meta", {"route": "rag", "sources": [{"unit_title": "U3", "score": 0.9}]})
        if debug:
            yield ("debug", {"route": "rag", "cache_hit": False})
        yield ("done", {"ok": True})

    monkeypatch.setattr("app.api.lesson_qa.iter_qa_turn_sse", fake_iter_qa_turn_sse)

    response = await client.post(
        f"/api/v1/lessons/{skill.id}/qa/messages",
        json={"content": "What does reservation mean?", "debug": True},
    )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    text = response.text
    assert text.index("event: token") < text.index("event: meta") < text.index("event: done")
    assert "A reservation " in text
    assert '"route": "rag"' in text
    assert "event: debug" in text
