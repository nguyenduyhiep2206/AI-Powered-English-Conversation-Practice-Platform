"""API tests for tutor SSE message streaming."""

from __future__ import annotations

from collections.abc import AsyncIterator

import pytest
import pytest_asyncio
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

pytest_plugins = ["tests.tutor.conftest"]

from app.api import tutor
from app.api.deps import get_current_active_user
from app.core.database import get_db
from app.models.enums import TutorSessionStatusEnum


@pytest_asyncio.fixture
async def api_client(db_session, tutor_seed, active_tutor_session):
    app = FastAPI()
    app.include_router(tutor.router, prefix="/api/v1/tutor")

    async def override_get_db():
        yield db_session

    async def override_current_user():
        return tutor_seed["user"]

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_active_user] = override_current_user

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client, active_tutor_session

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_get_session_includes_scenario(api_client):
    client, session = api_client

    response = await client.get(f"/api/v1/tutor/sessions/{session.id}")

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["scenario"]["id"] == session.scenario_id
    assert data["scenario"]["title"]
    assert data["scenario"]["ai_role"]
    assert data["scenario"]["user_role"]
    assert "goal_prompt" in data["scenario"]


@pytest.mark.asyncio
async def test_post_message_streams_token_meta_done(api_client, monkeypatch):
    client, session = api_client

    async def fake_iter_turn_sse(
        _db, _user_id, _session_id, _content, *, debug: bool = False
    ) -> AsyncIterator[tuple[str, dict]]:
        yield ("token", {"text": "Hello "})
        yield ("token", {"text": "there"})
        yield (
            "meta",
            {"correction": None, "hint": None, "goal_progress": "none"},
        )
        if debug:
            yield ("debug", {"route": "roleplay", "cache_hit": False})
        yield ("done", {"ok": True})

    monkeypatch.setattr("app.api.tutor.iter_turn_sse", fake_iter_turn_sse)

    response = await client.post(
        f"/api/v1/tutor/sessions/{session.id}/messages",
        json={"content": "Hi"},
    )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")

    text = response.text
    token_idx = text.index("event: token")
    meta_idx = text.index("event: meta")
    done_idx = text.index("event: done")
    assert token_idx < meta_idx < done_idx
    assert '"text": "Hello "' in text
    assert '"goal_progress": "none"' in text


@pytest_asyncio.fixture
async def api_client_inactive_session(db_session, tutor_seed, active_tutor_session):
    active_tutor_session.status = TutorSessionStatusEnum.completed
    await db_session.commit()
    await db_session.refresh(active_tutor_session)

    app = FastAPI()
    app.include_router(tutor.router, prefix="/api/v1/tutor")

    async def override_get_db():
        yield db_session

    async def override_current_user():
        return tutor_seed["user"]

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_active_user] = override_current_user

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client, active_tutor_session

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_post_message_returns_409_when_session_not_active(api_client_inactive_session):
    client, session = api_client_inactive_session

    response = await client.post(
        f"/api/v1/tutor/sessions/{session.id}/messages",
        json={"content": "Hi"},
    )

    assert response.status_code == 409
    assert response.json()["detail"] == "Tutor session is not active"


@pytest.mark.asyncio
async def test_end_session_returns_409_when_session_not_active(api_client_inactive_session):
    client, session = api_client_inactive_session

    response = await client.post(f"/api/v1/tutor/sessions/{session.id}/end")

    assert response.status_code == 409
    assert response.json()["detail"] == "Tutor session is not active"
