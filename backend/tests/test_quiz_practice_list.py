"""API tests for learner Practice question list — excludes writing / TOEIC W parts."""

from __future__ import annotations

import pytest
import pytest_asyncio
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import BigInteger
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.ext.compiler import compiles

import app.models  # noqa: F401
from app.api import quiz
from app.api.deps import get_current_active_user
from app.core.database import Base, get_db
from app.models.book import BookDB
from app.models.book_structure_preview import BookStructurePreviewDB
from app.models.enums import (
    CEFRLevel,
    QuizQuestionStatusEnum,
    QuizQuestionTypeEnum,
    ToeicPartEnum,
)
from app.models.learning_skill import LearningSkillDB
from app.models.quiz_question import QuizQuestionDB
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
        BookDB.__table__,
        BookStructurePreviewDB.__table__,
        QuizQuestionDB.__table__,
    ]
    async with engine.begin() as conn:
        await conn.run_sync(lambda sync_conn: Base.metadata.create_all(sync_conn, tables=tables))

    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        yield session

    await engine.dispose()


def _make_question(
    *,
    skill_id: int,
    book_id: int,
    unit_id: int,
    stem: str,
    question_type: QuizQuestionTypeEnum = QuizQuestionTypeEnum.mcq,
    toeic_part: ToeicPartEnum | None = None,
    task_brief: dict | None = None,
) -> QuizQuestionDB:
    return QuizQuestionDB(
        skill_id=skill_id,
        book_id=book_id,
        unit_id=unit_id,
        question_type=question_type,
        stem=stem,
        toeic_part=toeic_part,
        task_brief=task_brief,
        options=["a", "b"],
        answer="a",
        status=QuizQuestionStatusEnum.published,
    )


@pytest_asyncio.fixture
async def practice_seed(db_session: AsyncSession):
    user = UserDB(username="learner", email="learner@test.com", password_hash="x")
    db_session.add(user)
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

    book = BookDB(
        title="Test book",
        file_path="/tmp/test.pdf",
        file_size=100,
    )
    db_session.add(book)
    await db_session.flush()

    unit = BookStructurePreviewDB(
        book_id=book.id,
        unit_index=1,
        title="Unit 1",
        page_start=1,
        page_end=2,
        detection_method="manual",
        confidence=1.0,
    )
    db_session.add(unit)
    await db_session.flush()

    return {
        "user": user,
        "skill": skill,
        "book": book,
        "unit": unit,
    }


@pytest_asyncio.fixture
async def api_client(db_session: AsyncSession, practice_seed):
    app = FastAPI()
    app.include_router(quiz.router, prefix="/api/v1/quiz")

    async def override_get_db():
        yield db_session

    async def override_current_user():
        return practice_seed["user"]

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_active_user] = override_current_user

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client, practice_seed

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_excludes_writing_question_type(api_client, db_session):
    client, seed = api_client
    sid, bid, uid = seed["skill"].id, seed["book"].id, seed["unit"].id

    db_session.add_all(
        [
            _make_question(
                skill_id=sid,
                book_id=bid,
                unit_id=uid,
                stem="Pick the article",
                task_brief={"mode": "skill_drill", "item_kind": "form_choose"},
            ),
            _make_question(
                skill_id=sid,
                book_id=bid,
                unit_id=uid,
                stem="Write an email reply",
                question_type=QuizQuestionTypeEnum.writing,
                toeic_part=ToeicPartEnum.w2,
                task_brief={"mode": "toeic_writing"},
            ),
        ]
    )
    await db_session.commit()

    response = await client.get(f"/api/v1/quiz/skills/{sid}/questions?limit=10")

    assert response.status_code == 200
    data = response.json()["data"]
    assert len(data) == 1
    assert data[0]["question_type"] == "mcq"
    assert data[0]["stem"] == "Pick the article"
    assert all(row["question_type"] != "writing" for row in data)


@pytest.mark.asyncio
async def test_excludes_toeic_writing_parts_even_when_not_writing_type(api_client, db_session):
    client, seed = api_client
    sid, bid, uid = seed["skill"].id, seed["book"].id, seed["unit"].id

    db_session.add_all(
        [
            _make_question(
                skill_id=sid,
                book_id=bid,
                unit_id=uid,
                stem="Allowed mcq",
            ),
            _make_question(
                skill_id=sid,
                book_id=bid,
                unit_id=uid,
                stem="W2 email task",
                question_type=QuizQuestionTypeEnum.mcq,
                toeic_part=ToeicPartEnum.w2,
            ),
        ]
    )
    await db_session.commit()

    response = await client.get(f"/api/v1/quiz/skills/{sid}/questions?limit=10")

    assert response.status_code == 200
    stems = {row["stem"] for row in response.json()["data"]}
    assert stems == {"Allowed mcq"}
    assert all(row.get("toeic_part") not in ("w1", "w2", "w3") for row in response.json()["data"])


@pytest.mark.asyncio
async def test_returns_item_kind_from_task_brief(api_client, db_session):
    client, seed = api_client
    sid, bid, uid = seed["skill"].id, seed["book"].id, seed["unit"].id

    db_session.add(
        _make_question(
            skill_id=sid,
            book_id=bid,
            unit_id=uid,
            stem="Cloze item",
            question_type=QuizQuestionTypeEnum.cloze,
            task_brief={"mode": "skill_drill", "item_kind": "cloze_form"},
        )
    )
    await db_session.commit()

    response = await client.get(f"/api/v1/quiz/skills/{sid}/questions?limit=5")

    assert response.status_code == 200
    row = response.json()["data"][0]
    assert row["item_kind"] == "cloze_form"


@pytest.mark.asyncio
async def test_prefers_skill_drill_when_enough_published(api_client, db_session):
    client, seed = api_client
    sid, bid, uid = seed["skill"].id, seed["book"].id, seed["unit"].id

    db_session.add_all(
        [
            _make_question(
                skill_id=sid,
                book_id=bid,
                unit_id=uid,
                stem=f"skill_drill {i}",
                task_brief={"mode": "skill_drill", "item_kind": "form_choose"},
            )
            for i in range(3)
        ]
        + [
            _make_question(
                skill_id=sid,
                book_id=bid,
                unit_id=uid,
                stem=f"legacy {i}",
                task_brief=None,
            )
            for i in range(3)
        ]
    )
    await db_session.commit()

    response = await client.get(f"/api/v1/quiz/skills/{sid}/questions?limit=3")

    assert response.status_code == 200
    data = response.json()["data"]
    assert len(data) == 3
    assert all(row["stem"].startswith("skill_drill") for row in data)
    assert all(row["item_kind"] == "form_choose" for row in data)
