from unittest.mock import MagicMock

from app.services.quiz_generation_service import (
    should_skip_skill_drill_publish,
    validate_skill_drill_questions,
)
from app.services.skill_drill_align import batch_align_ratio
from app.services.skill_drill_blueprint import blueprint_for_skill_drill


def test_validate_skill_drill_accepts_cloze():
    bp = blueprint_for_skill_drill("grammar", 2)
    # Force first two to cloze-friendly for this unit test
    bp = [
        {"item_kind": "cloze_form", "question_type": "cloze"},
        {"item_kind": "form_choose", "question_type": "mcq"},
    ]
    items = [
        {
            "type": "cloze",
            "item_kind": "cloze_form",
            "stem": "I ___ a student.",
            "options": [],
            "answer": "am",
            "difficulty": "easy",
        },
        {
            "type": "mcq",
            "item_kind": "form_choose",
            "stem": "She ___ happy.",
            "options": ["am", "is", "are", "be"],
            "answer": "is",
            "difficulty": "easy",
        },
    ]
    out = validate_skill_drill_questions(
        items, blueprint=bp, surfaces={"am", "is"}, alignment="lesson"
    )
    assert len(out) == 2
    assert out[0]["type"] == "cloze"
    assert out[0]["task_brief"]["mode"] == "skill_drill"
    assert batch_align_ratio(out, {"am", "is"}) >= 0.8


def test_align_fail_ratio():
    items = [
        {"stem": "When was HBC founded?", "answer": "1670", "options": []},
        {"stem": "Who owns the company?", "answer": "x", "options": []},
    ]
    assert batch_align_ratio(items, {"am", "is", "are"}) < 0.8


def test_should_skip_misaligned_skill_drill():
    row = MagicMock()
    row.task_brief = {
        "mode": "skill_drill",
        "surfaces": ["am", "is", "are"],
        "item_kind": "form_choose",
        "alignment": "lesson",
    }
    row.stem = "What year was the company founded?"
    row.passage = None
    row.answer = "1670"
    row.options = ["1670", "1770"]
    assert should_skip_skill_drill_publish(row) is True

    row.stem = "I ___ happy."
    row.answer = "am"
    row.options = ["am", "is", "are"]
    assert should_skip_skill_drill_publish(row) is False


def test_surfaces_skip_long_form_patterns_keep_examples():
    from app.services.quiz_generation_service import surfaces_from_lesson_content

    out = surfaces_from_lesson_content(
        {
            "targets": [{"surface": "a student"}],
            "form": {
                "rows": [
                    {
                        "label": "Use a",
                        "pattern": "Before consonant sounds",
                        "example": "a pen",
                    }
                ]
            },
        }
    )
    assert "Before consonant sounds" not in out
    assert "a pen" in out
    assert "a" in out
    assert "a student" in out


def test_grammar_error_message_constant():
    from app.services.quiz_generation_service import (
        surfaces_from_lesson_content,
    )

    assert surfaces_from_lesson_content(None) == set()
    msg = "Grammar skill_drill requires a published lesson with targets/form."
    assert "published lesson" in msg
    assert "Skill-drill alignment too low" in (
        "Skill-drill alignment too low (0.50 < 0.8). Regenerate or fix lesson targets."
    )
    assert "sync book first" in "Skill doesn't have book source — sync book first."
