"""Async SQLite fixtures for tutor service tests."""

from __future__ import annotations

import pytest
import pytest_asyncio
from sqlalchemy import BigInteger
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.ext.compiler import compiles

import app.models  # noqa: F401 — register metadata
from app.core.database import Base


@compiles(BigInteger, "sqlite")
def _sqlite_bigint(type_, compiler, **kw):
    return "INTEGER"
from app.models.enums import (
    CEFRLevel,
    GoalEnum,
    ScenarioCategoryEnum,
    TutorMessageRoleEnum,
    TutorSessionStatusEnum,
)
from app.models.learning_skill import LearningSkillDB
from app.models.profile import UserProfileDB
from app.models.roadmap_step_skill import RoadmapStepSkillDB
from app.models.scenario import RoadmapStepDB, ScenarioDB, UserProgressDB
from app.models.tutor import TutorMessageDB, TutorSessionDB
from app.models.user import UserDB
from app.models.user_skill_mastery import UserSkillMasteryDB


@pytest_asyncio.fixture
async def db_session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    tutor_tables = [
        UserDB.__table__,
        UserProfileDB.__table__,
        ScenarioDB.__table__,
        RoadmapStepDB.__table__,
        UserProgressDB.__table__,
        LearningSkillDB.__table__,
        RoadmapStepSkillDB.__table__,
        UserSkillMasteryDB.__table__,
        TutorSessionDB.__table__,
        TutorMessageDB.__table__,
    ]
    async with engine.begin() as conn:
        await conn.run_sync(lambda sync_conn: Base.metadata.create_all(sync_conn, tables=tutor_tables))

    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        yield session

    await engine.dispose()


@pytest_asyncio.fixture
async def tutor_seed(db_session: AsyncSession):
    user = UserDB(username="learner", email="learner@test.com", password_hash="x")
    db_session.add(user)
    await db_session.flush()

    db_session.add(
        UserProfileDB(
            user_id=user.id,
            goal=GoalEnum.daily_conversation,
            current_level=CEFRLevel.A1,
            survey_done=True,
        )
    )

    scenario = ScenarioDB(
        title="Hotel check-in",
        slug="hotel-checkin-test",
        category=ScenarioCategoryEnum.hotel,
        level=CEFRLevel.A1,
        ai_role="Hotel receptionist",
        user_role="Guest",
        goal_prompt="Check into your room and ask about breakfast.",
        suggested_vocab=["reservation", "key"],
        order_index=1,
        is_active=True,
    )
    db_session.add(scenario)
    await db_session.flush()

    step = RoadmapStepDB(
        level=CEFRLevel.A1,
        week_number=1,
        title="Week 1",
        scenario_id=scenario.id,
    )
    db_session.add(step)
    await db_session.flush()

    skill = LearningSkillDB(
        slug="articles-a1",
        title="Articles",
        cefr_level=CEFRLevel.A1,
        skill_type="grammar",
        difficulty_in_level=2,
        is_active=True,
    )
    db_session.add(skill)
    await db_session.flush()

    db_session.add(
        RoadmapStepSkillDB(roadmap_step_id=step.id, skill_id=skill.id, role="quiz")
    )
    db_session.add(
        UserSkillMasteryDB(user_id=user.id, skill_id=skill.id, mastery=0.3, attempts=1, correct=0)
    )
    await db_session.commit()

    return {
        "user": user,
        "scenario": scenario,
        "step": step,
        "skill": skill,
    }


@pytest_asyncio.fixture
async def active_tutor_session(db_session: AsyncSession, tutor_seed):
    session = TutorSessionDB(
        user_id=tutor_seed["user"].id,
        roadmap_step_id=None,
        scenario_id=tutor_seed["scenario"].id,
        status=TutorSessionStatusEnum.active,
        target_skill_ids=[tutor_seed["skill"].id],
        message_count=0,
    )
    db_session.add(session)
    await db_session.flush()
    db_session.add(
        TutorMessageDB(
            session_id=session.id,
            role=TutorMessageRoleEnum.assistant,
            content="Welcome! I'm the Hotel receptionist.",
            meta=None,
        )
    )
    await db_session.commit()
    await db_session.refresh(session)
    return session
