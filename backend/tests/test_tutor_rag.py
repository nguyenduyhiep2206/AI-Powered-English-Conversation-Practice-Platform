"""Unit tests for tutor RAG helpers."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from app.services.tutor_memory import estimate_tokens, window_transcript
from app.services.tutor_rag import (
    cosine,
    format_retrieved_block,
    is_off_topic,
    needs_rag,
    retrieve_for_session,
    select_top_chunks,
)
from app.services.tutor_rag_cache import cache_key, normalize_query


def test_is_off_topic_gold_and_news():
    assert is_off_topic("What's the gold price today?")
    assert is_off_topic("giá vàng hôm nay bao nhiêu?")
    assert is_off_topic("Any breaking news?")
    assert not is_off_topic("I have a reservation under Lee.")
    assert not is_off_topic("Can I have the breakfast menu?")


def test_needs_rag_hints():
    assert needs_rag("What does 'reservation' mean?")
    assert needs_rag("Can you explain this grammar?")
    assert not needs_rag("Hi")
    assert not needs_rag("Okay")


def test_cosine_and_select_top():
    q = [1.0, 0.0, 0.0]
    docs = [
        {"embedding": [0.9, 0.1, 0.0], "text": "alpha " * 20, "unit_title": "A", "_id": "1"},
        {"embedding": [0.0, 1.0, 0.0], "text": "beta " * 20, "unit_title": "B", "_id": "2"},
        {"embedding": [0.8, 0.2, 0.0], "text": "gamma " * 20, "unit_title": "C", "_id": "3"},
    ]
    assert cosine(q, q) == 1.0
    top = select_top_chunks(q, docs, top_k=2, min_score=0.5, max_chars=500)
    assert len(top) == 2
    assert top[0]["unit_title"] == "A"
    assert format_retrieved_block(top).startswith("[1]")


def test_window_transcript_keeps_opener_and_tail():
    msgs = [{"role": "assistant", "content": "Opener"}]
    for i in range(10):
        msgs.append({"role": "user", "content": f"u{i}"})
        msgs.append({"role": "assistant", "content": f"a{i}"})
    windowed = window_transcript(msgs, max_turns=2, keep_first_assistant=True)
    assert windowed[0]["content"] == "Opener"
    assert windowed[-1]["content"] == "a9"
    assert len(windowed) <= 1 + 4


def test_cache_key_stable():
    assert normalize_query("  Hello   World ") == "hello world"
    a = cache_key("hello", [3, 1, 2])
    b = cache_key("hello", [1, 2, 3])
    assert a == b
    assert a.startswith("tutor:rag:")


@pytest.mark.asyncio
async def test_retrieve_for_session_enabled_override(monkeypatch):
    monkeypatch.setattr("app.services.tutor_rag.settings.TUTOR_RAG_ENABLED", False)

    async def fake_scope(db, skill_ids):
        return [(1, 2)]

    monkeypatch.setattr("app.services.tutor_rag.resolve_unit_scope", fake_scope)
    monkeypatch.setattr(
        "app.services.tutor_rag.load_embedded_chunks",
        lambda scope, limit_per_unit=40: [
            {"embedding": [1.0, 0.0], "text": "hello world", "unit_title": "U1", "_id": "1"}
        ],
    )
    monkeypatch.setattr("app.services.tutor_rag.embed_texts", lambda qs: [[1.0, 0.0]])

    db = MagicMock()
    query = "What does reservation mean?"

    assert await retrieve_for_session(db, skill_ids=[1], query=query) == []
    result = await retrieve_for_session(db, skill_ids=[1], query=query, enabled=True)
    assert len(result) == 1
    assert result[0]["unit_title"] == "U1"


def test_hybrid_token_budget_under_half_baseline():
    """Fixture: long history + fat unit pack vs window + top-k excerpts."""
    opener = {"role": "assistant", "content": "Welcome to check-in."}
    history = [opener]
    for i in range(30):
        history.append({"role": "user", "content": f"Learner turn {i} with filler text about rooms and keys."})
        history.append(
            {
                "role": "assistant",
                "content": f"Front desk reply {i} confirming details and asking a follow-up question.",
            }
        )
    unit_pack = ("Unit text about hotels, breakfast, reservations. " * 200).strip()

    baseline_text = (
        "\n".join(f"{m['role']}: {m['content']}" for m in history) + "\n\n" + unit_pack
    )
    hybrid_msgs = window_transcript(history, max_turns=6, keep_first_assistant=True)
    hybrid_rag = format_retrieved_block(
        [
            {"score": 0.9, "unit_title": "Check-in", "text": unit_pack[:600]},
            {"score": 0.8, "unit_title": "Breakfast", "text": unit_pack[600:1200]},
            {"score": 0.7, "unit_title": "Keys", "text": unit_pack[1200:1800]},
            {"score": 0.6, "unit_title": "Lobby", "text": unit_pack[1800:2400]},
        ]
    )
    hybrid_text = (
        "\n".join(f"{m['role']}: {m['content']}" for m in hybrid_msgs) + "\n\n" + hybrid_rag
    )

    baseline_tokens = estimate_tokens(baseline_text)
    hybrid_tokens = estimate_tokens(hybrid_text)
    assert baseline_tokens > 0
    assert hybrid_tokens <= 0.5 * baseline_tokens
