from app.services.tutor_prompt import META_DELIMITER, filter_soft_signals, split_reply_and_meta


def test_split_reply_and_meta_happy():
    raw = "Hello there!" + META_DELIMITER + '{"correction":null,"hint":null,"goal_progress":"none"}'
    reply, meta = split_reply_and_meta(raw)
    assert reply == "Hello there!"
    assert meta["goal_progress"] == "none"


def test_split_without_meta_defaults():
    reply, meta = split_reply_and_meta("Only text")
    assert reply == "Only text"
    assert meta["correction"] is None


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
