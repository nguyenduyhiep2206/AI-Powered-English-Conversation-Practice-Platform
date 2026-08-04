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
async def test_post_message_streams_token_meta_done(api_client, monkeypatch):
    client, session = api_client

    async def fake_iter_turn_sse(
        _db, _user_id, _session_id, _content
    ) -> AsyncIterator[tuple[str, dict]]:
        yield ("token", {"text": "Hello "})
        yield ("token", {"text": "there"})
        yield (
            "meta",
            {"correction": None, "hint": None, "goal_progress": "none"},
        )
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
