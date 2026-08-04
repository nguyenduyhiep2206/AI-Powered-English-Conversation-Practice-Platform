from app.services.tutor_prompt import META_DELIMITER, build_turn_user_payload, filter_soft_signals, split_reply_and_meta


def test_build_turn_user_payload_uses_transcript_only():
    transcript = [
        {"role": "assistant", "content": "Welcome!"},
        {"role": "user", "content": "I have a reservation."},
    ]
    payload = build_turn_user_payload(transcript=transcript)
    assert payload.count("user: I have a reservation.") == 1
    assert "Welcome!" in payload


def test_split_reply_and_meta_happy():
    raw = "Hello there!" + META_DELIMITER + '{"correction":null,"hint":null,"goal_progress":"none"}'
    reply, meta = split_reply_and_meta(raw)
    assert reply == "Hello there!"
    assert meta["goal_progress"] == "none"


def test_split_without_meta_defaults():
    reply, meta = split_reply_and_meta("Only text")
    assert reply == "Only text"
    assert meta["correction"] is None
    assert meta["off_topic"] is False


def test_build_turn_system_includes_retrieved_and_off_topic():
    from app.services.tutor_prompt import build_turn_system_prompt

    prompt = build_turn_system_prompt(
        cefr_level="A1",
        ai_role="Waiter",
        user_role="Guest",
        goal_prompt="Order food",
        suggested_vocab=["menu"],
        target_skill_titles=["Polite requests"],
        retrieved_context="[1] (Food)\nPlease",
        force_off_topic_redirect=True,
    )
    assert "OFF-TOPIC" in prompt
    assert "[1] (Food)" in prompt
    assert "off_topic" in prompt


def test_filter_soft_signals_drops_unknown_skills():
    out = filter_soft_signals(
        [
            {"skill_id": 1, "signal": "needs_practice", "note": "x"},
            {"skill_id": 99, "signal": "needs_practice", "note": "y"},
        ],
        {1},
    )
    assert out == [{"skill_id": 1, "signal": "needs_practice", "note": "x"}]


def test_split_reply_and_meta_non_dict_defaults():
    raw = "Hello!" + META_DELIMITER + '["not", "a", "dict"]'
    reply, meta = split_reply_and_meta(raw)
    assert reply == "Hello!"
    assert meta["correction"] is None
    assert meta["hint"] is None
    assert meta["goal_progress"] == "none"
