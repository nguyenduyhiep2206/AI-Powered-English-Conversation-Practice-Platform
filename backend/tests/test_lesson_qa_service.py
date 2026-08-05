"""Tests for Lesson Q&A ensure / get / clear orchestration."""

from __future__ import annotations

import pytest
import pytest_asyncio
from sqlalchemy import BigInteger, select
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.ext.compiler import compiles

import app.models  # noqa: F401 — register metadata
from app.core.database import Base
from app.models.enums import (
    CEFRLevel,
    LessonQaMessageRoleEnum,
    LessonQaSessionStatusEnum,
)
from app.models.learning_skill import LearningSkillDB
from app.models.lesson_qa import LessonQaMessageDB, LessonQaSessionDB
from app.models.skill_lesson import (
    SkillLessonDB,
    UserLessonPackProgressDB,
    UserLessonProgressDB,
)
from app.models.user import UserDB
from app.services.lesson_qa_service import (
    clear_messages,
    get_or_create_session,
    get_qa_bundle,
    _target_surfaces,
)


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
        UserLessonProgressDB.__table__,
        UserLessonPackProgressDB.__table__,
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
    await db_session.flush()

    lesson = SkillLessonDB(
        skill_id=skill.id,
        pack_index=0,
        title="Book a table",
        objective="Ask for a table politely",
        content={
            "targets": [
                {"surface": "reservation", "gloss": "booking"},
                {"surface": "I'd like", "gloss": "want"},
            ]
        },
        status="published",
    )
    db_session.add(lesson)
    await db_session.commit()

    return {"user": user, "skill": skill, "lesson": lesson}


def test_target_surfaces_extracts_surfaces():
    assert _target_surfaces(
        {"targets": [{"surface": "a"}, {"surface": "  "}, "x", {"surface": "b"}]}
    ) == ["a", "b"]
    assert _target_surfaces(None) == []
    assert _target_surfaces({"targets": "nope"}) == []


@pytest.mark.asyncio
async def test_get_or_create_session_idempotent(db_session, qa_seed):
    user_id = qa_seed["user"].id
    skill_id = qa_seed["skill"].id

    first = await get_or_create_session(db_session, user_id, skill_id)
    second = await get_or_create_session(db_session, user_id, skill_id)

    assert first.id == second.id
    assert first.status == LessonQaSessionStatusEnum.active
    assert first.message_count == 0

    rows = list(
        (
            await db_session.execute(
                select(LessonQaSessionDB).where(
                    LessonQaSessionDB.user_id == user_id,
                    LessonQaSessionDB.skill_id == skill_id,
                )
            )
        )
        .scalars()
        .all()
    )
    assert len(rows) == 1


@pytest.mark.asyncio
async def test_get_or_create_session_missing_skill(db_session, qa_seed):
    with pytest.raises(ValueError, match="Skill not found"):
        await get_or_create_session(db_session, qa_seed["user"].id, skill_id=999999)


@pytest.mark.asyncio
async def test_get_qa_bundle_includes_suggestions_and_messages(db_session, qa_seed):
    user_id = qa_seed["user"].id
    skill_id = qa_seed["skill"].id

    session = await get_or_create_session(db_session, user_id, skill_id)
    db_session.add(
        LessonQaMessageDB(
            session_id=session.id,
            role=LessonQaMessageRoleEnum.user,
            content="What does reservation mean?",
            meta=None,
        )
    )
    session.message_count = 1
    await db_session.commit()

    bundle = await get_qa_bundle(db_session, user_id, skill_id)
    assert bundle["session"].id == session.id
    assert len(bundle["messages"]) == 1
    assert bundle["messages"][0].content == "What does reservation mean?"
    prompts = bundle["suggested_prompts"]
    assert 3 <= len(prompts) <= 5
    assert any("reservation" in p for p in prompts)


@pytest.mark.asyncio
async def test_get_qa_bundle_suggestions_use_current_pack(db_session, qa_seed):
    user_id = qa_seed["user"].id
    skill_id = qa_seed["skill"].id

    db_session.add(
        SkillLessonDB(
            skill_id=skill_id,
            pack_index=1,
            title="Confirm a booking",
            objective="Confirm reservation details",
            content={
                "targets": [
                    {"surface": "confirm", "gloss": "xác nhận"},
                    {"surface": "booking", "gloss": "đặt chỗ"},
                ]
            },
            status="published",
        )
    )
    db_session.add(
        UserLessonPackProgressDB(
            user_id=user_id,
            skill_id=skill_id,
            pack_index=0,
        )
    )
    await db_session.commit()

    bundle = await get_qa_bundle(db_session, user_id, skill_id)
    prompts = bundle["suggested_prompts"]
    assert any('What does "confirm" mean?' in p or 'What does "booking" mean?' in p for p in prompts)
    assert not any('What does "reservation" mean?' in p for p in prompts)


@pytest.mark.asyncio
async def test_clear_messages_empties_transcript(db_session, qa_seed):
    user_id = qa_seed["user"].id
    skill_id = qa_seed["skill"].id

    session = await get_or_create_session(db_session, user_id, skill_id)
    db_session.add(
        LessonQaMessageDB(
            session_id=session.id,
            role=LessonQaMessageRoleEnum.assistant,
            content="A reservation is a booking.",
            meta={"sources": []},
        )
    )
    session.message_count = 1
    await db_session.commit()

    await clear_messages(db_session, user_id, skill_id)

    remaining = list(
        (
            await db_session.execute(
                select(LessonQaMessageDB).where(
                    LessonQaMessageDB.session_id == session.id
                )
            )
        )
        .scalars()
        .all()
    )
    assert remaining == []
    await db_session.refresh(session)
    assert session.message_count == 0
