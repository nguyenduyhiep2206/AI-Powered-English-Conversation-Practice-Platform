"""Unit tests for skill_drill LLM verifier (mocked chat_json)."""

from unittest.mock import patch

from app.services.skill_drill_verifier import (
    kinds_needing_verify,
    verify_skill_drill_items,
)


def test_kinds_needing_verify():
    assert kinds_needing_verify({"item_kind": "spot_error"}) is True
    assert kinds_needing_verify({"item_kind": "fix_grammar"}) is True
    assert kinds_needing_verify({"item_kind": "form_choose"}) is False


def test_flag_off_passthrough():
    items = [
        {
            "item_kind": "spot_error",
            "type": "mcq",
            "stem": "My sister is drinking coffee, but she usually works.",
            "options": ["is drinking", "coffee", "usually", "works"],
            "answer": "works",
            "explanation": "x",
            "task_brief": {"mode": "skill_drill", "item_kind": "spot_error"},
        }
    ]
    with patch("app.services.skill_drill_verifier.settings") as settings:
        settings.SKILL_DRILL_LLM_VERIFY = False
        with patch("app.services.skill_drill_verifier.chat_json") as chat:
            out = verify_skill_drill_items(
                items, skill_title="Present Continuous", cefr="A1"
            )
            chat.assert_not_called()
    assert out == items


def test_rejects_false_spot_error():
    items = [
        {
            "item_kind": "form_choose",
            "type": "mcq",
            "stem": "She ___ happy.",
            "options": ["is", "am"],
            "answer": "is",
            "task_brief": {"mode": "skill_drill", "item_kind": "form_choose"},
        },
        {
            "item_kind": "spot_error",
            "type": "mcq",
            "stem": "My sister is drinking coffee, but she usually works in the morning.",
            "options": ["is drinking", "coffee", "usually", "works"],
            "answer": "works",
            "explanation": "Error: works / Correct: works",
            "task_brief": {"mode": "skill_drill", "item_kind": "spot_error"},
        },
    ]
    with patch("app.services.skill_drill_verifier.settings") as settings:
        settings.SKILL_DRILL_LLM_VERIFY = True
        with patch(
            "app.services.skill_drill_verifier.chat_json",
            return_value={
                "results": [{"index": 0, "pass": False, "reason": "no error"}]
            },
        ) as chat:
            out = verify_skill_drill_items(
                items, skill_title="PC", cefr="A1"
            )
            assert chat.call_count >= 1
    assert len(out) == 1
    assert out[0]["item_kind"] == "form_choose"


def test_accepts_real_spot_error_marks_verified():
    items = [
        {
            "item_kind": "spot_error",
            "type": "mcq",
            "stem": "My father work in an office, but today he is staying at home.",
            "options": ["work", "in an office", "is staying", "at home"],
            "answer": "work",
            "explanation": "Error: work / Correct: works / Why: 3sg -s.",
            "task_brief": {"mode": "skill_drill", "item_kind": "spot_error"},
        }
    ]
    with patch("app.services.skill_drill_verifier.settings") as settings:
        settings.SKILL_DRILL_LLM_VERIFY = True
        with patch(
            "app.services.skill_drill_verifier.chat_json",
            return_value={
                "results": [{"index": 0, "pass": True, "reason": "ok"}]
            },
        ):
            out = verify_skill_drill_items(items, skill_title="PC", cefr="A1")
    assert len(out) == 1
    assert out[0]["task_brief"]["verified"] is True


def test_omitted_index_fail_closed():
    items = [
        {
            "item_kind": "spot_error",
            "type": "mcq",
            "stem": "They is here now.",
            "options": ["They", "is", "here", "now"],
            "answer": "is",
            "explanation": "Error: is / Correct: are / Why: plural.",
            "task_brief": {"mode": "skill_drill", "item_kind": "spot_error"},
        }
    ]
    with patch("app.services.skill_drill_verifier.settings") as settings:
        settings.SKILL_DRILL_LLM_VERIFY = True
        with patch(
            "app.services.skill_drill_verifier.chat_json",
            return_value={"results": []},
        ):
            out = verify_skill_drill_items(items, skill_title="PC", cefr="A1")
    assert out == []
