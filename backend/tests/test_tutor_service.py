"""Tests for tutor session orchestration."""

from __future__ import annotations

import pytest

pytest_plugins = ["tests.tutor.conftest"]

from sqlalchemy import select

from app.models.enums import TutorSessionStatusEnum
from app.models.tutor import TutorMessageDB
from app.models.user_skill_mastery import UserSkillMasteryDB
from app.core.config import settings
from app.services.tutor_prompt import META_DELIMITER
from app.services.tutor_service import (
    end_session,
    iter_turn_sse,
    snapshot_user_mastery,
    start_session,
)


@pytest.mark.asyncio
async def test_start_creates_session_with_opener(db_session, tutor_seed):
    session = await start_session(
        db_session,
        tutor_seed["user"].id,
        scenario_id=tutor_seed["scenario"].id,
    )
    assert session.status == TutorSessionStatusEnum.active
    assert session.roadmap_step_id is None
    assert session.target_skill_ids == []
    assert session.message_count == 0

    messages = (
        await db_session.execute(
            select(TutorMessageDB).where(TutorMessageDB.session_id == session.id)
        )
    ).scalars().all()
    assert len(messages) == 1
    assert messages[0].role.value == "assistant"
    assert "Hotel receptionist" in messages[0].content


@pytest.mark.asyncio
async def test_end_filters_unknown_skill_ids(monkeypatch, db_session, active_tutor_session, tutor_seed):
    user_id = tutor_seed["user"].id

    def fake_chat_json(system, user):
        return {
            "went_well": ["ok"],
            "fix_next": ["articles"],
            "soft_skill_signals": [
                {
                    "skill_id": active_tutor_session.target_skill_ids[0],
                    "signal": "needs_practice",
                    "note": "a",
                },
                {"skill_id": 999999, "signal": "needs_practice", "note": "bad"},
            ],
        }

    monkeypatch.setattr("app.services.tutor_service.chat_json", fake_chat_json)
    summary = await end_session(db_session, user_id, active_tutor_session.id)
    assert all(s["skill_id"] != 999999 for s in summary["soft_skill_signals"])
    assert len(summary["soft_skill_signals"]) == 1


@pytest.mark.asyncio
async def test_end_does_not_touch_mastery(monkeypatch, db_session, active_tutor_session, tutor_seed):
    user_id = tutor_seed["user"].id
    before = await snapshot_user_mastery(db_session, user_id)

    def fake_chat_json(system, user):
        return {
            "went_well": ["good"],
            "fix_next": [],
            "soft_skill_signals": [],
        }

    monkeypatch.setattr("app.services.tutor_service.chat_json", fake_chat_json)
    await end_session(db_session, user_id, active_tutor_session.id)
    after = await snapshot_user_mastery(db_session, user_id)
    assert before == after


@pytest.mark.asyncio
async def test_start_by_scenario_id_catalog(db_session, tutor_seed):
    session = await start_session(
        db_session,
        tutor_seed["user"].id,
        scenario_id=tutor_seed["scenario"].id,
    )
    assert session.roadmap_step_id is None
    assert session.scenario_id == tutor_seed["scenario"].id
    assert session.target_skill_ids == []
    assert session.status == TutorSessionStatusEnum.active


@pytest.mark.asyncio
async def test_start_rejects_inactive_scenario(db_session, tutor_seed):
    scenario = tutor_seed["scenario"]
    scenario.is_active = False
    await db_session.commit()

    with pytest.raises(ValueError, match="not active"):
        await start_session(
            db_session,
            tutor_seed["user"].id,
            scenario_id=scenario.id,
        )


@pytest.mark.asyncio
async def test_iter_turn_sse_off_topic_sets_meta_and_debug(
    monkeypatch, db_session, active_tutor_session, tutor_seed
):
    user_id = tutor_seed["user"].id
    meta_json = '{"correction":null,"hint":null,"goal_progress":"none","off_topic":true}'
    full = f"Let's stick to your order.{META_DELIMITER}{meta_json}"

    async def fake_stream(*, system, user):
        assert "OFF-TOPIC" in system
        for ch in full:
            yield ch

    monkeypatch.setattr("app.services.tutor_service.chat_stream_text", fake_stream)

    events = []
    async for event, payload in iter_turn_sse(
        db_session,
        user_id,
        active_tutor_session.id,
        "What is the gold price today?",
        debug=True,
    ):
        events.append((event, payload))

    by_name = {e: p for e, p in events}
    assert by_name["meta"]["off_topic"] is True
    assert by_name["debug"]["route"] == "off_topic"
    assert events[-1][0] == "done"


@pytest.mark.asyncio
async def test_iter_turn_sse_streams_tokens_before_meta(monkeypatch, db_session, active_tutor_session, tutor_seed):
    user_id = tutor_seed["user"].id
    meta_json = '{"correction":null,"hint":null,"goal_progress":"partial"}'
    full = f"Hello there!{META_DELIMITER}{meta_json}"

    async def fake_stream(*, system, user):
        for ch in full:
            yield ch

    monkeypatch.setattr("app.services.tutor_service.chat_stream_text", fake_stream)

    events = []
    async for event, payload in iter_turn_sse(
        db_session, user_id, active_tutor_session.id, "I have a reservation."
    ):
        events.append((event, payload))

    event_names = [e for e, _ in events]
    assert event_names[0] == "user_message"
    assert "token" in event_names
    assert META_DELIMITER not in "".join(p.get("text", "") for e, p in events if e == "token")
    assert "meta" in event_names
    assert "assistant_message" in event_names
    assert event_names[-1] == "done"
    assert "debug" not in event_names

    await db_session.refresh(active_tutor_session)
    assert active_tutor_session.message_count == 1

    meta_idx = event_names.index("meta")
    assistant_idx = event_names.index("assistant_message")
    assert meta_idx < assistant_idx


@pytest.mark.asyncio
async def test_iter_turn_sse_yields_error_on_llm_failure(
    monkeypatch, db_session, active_tutor_session, tutor_seed
):
    user_id = tutor_seed["user"].id

    async def boom(*, system, user):
        raise RuntimeError("LLM down")
        yield ""  # pragma: no cover

    monkeypatch.setattr("app.services.tutor_service.chat_stream_text", boom)

    events = []
    async for event, payload in iter_turn_sse(
        db_session, user_id, active_tutor_session.id, "Hi"
    ):
        events.append((event, payload))

    assert events[0][0] == "user_message"
    assert any(e == "error" for e, _ in events)
    await db_session.refresh(active_tutor_session)
    assert active_tutor_session.message_count == 1
    user_msgs = (
        await db_session.execute(
            select(TutorMessageDB).where(
                TutorMessageDB.session_id == active_tutor_session.id,
                TutorMessageDB.role == "user",
            )
        )
    ).scalars().all()
    assert len(user_msgs) == 1


@pytest.mark.asyncio
async def test_iter_turn_sse_flushes_tokens_without_meta_delimiter(
    monkeypatch, db_session, active_tutor_session, tutor_seed
):
    """Reply with no META_DELIMITER must still emit all held-back tail chars."""
    user_id = tutor_seed["user"].id
    full_reply = "Hello there!"

    async def fake_stream(*, system, user):
        for ch in ["Hel", "lo ", "there!"]:
            yield ch

    monkeypatch.setattr("app.services.tutor_service.chat_stream_text", fake_stream)

    events = []
    async for event, payload in iter_turn_sse(
        db_session, user_id, active_tutor_session.id, "Hi"
    ):
        events.append((event, payload))

    token_text = "".join(p["text"] for e, p in events if e == "token")
    assert token_text == full_reply
    assert META_DELIMITER not in token_text


@pytest.mark.asyncio
async def test_iter_turn_sse_rejects_message_over_max_chars(
    db_session, active_tutor_session, tutor_seed
):
    user_id = tutor_seed["user"].id
    too_long = "x" * (settings.TUTOR_MAX_MESSAGE_CHARS + 1)

    with pytest.raises(ValueError, match="maximum length"):
        async for _ in iter_turn_sse(
            db_session, user_id, active_tutor_session.id, too_long
        ):
            pass


@pytest.mark.asyncio
async def test_iter_turn_sse_rejects_when_max_user_turns_reached(
    db_session, active_tutor_session, tutor_seed
):
    user_id = tutor_seed["user"].id
    active_tutor_session.message_count = settings.TUTOR_MAX_USER_TURNS
    await db_session.commit()

    with pytest.raises(ValueError, match="Maximum user turns"):
        async for _ in iter_turn_sse(
            db_session, user_id, active_tutor_session.id, "One more turn"
        ):
            pass
