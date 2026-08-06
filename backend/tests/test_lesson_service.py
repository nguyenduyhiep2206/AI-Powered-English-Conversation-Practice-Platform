from app.services.lesson_service import (
    attach_quiz_book_badges,
    compute_can_skip,
    compute_learn_available,
)
from app.services.lesson_writing_feedback import (
    feedback_on_writing,
    writing_context_from_lesson_content,
)


def test_attach_quiz_book_badges_defaults_and_lookup():
    rows = [
        {
            "skill_id": 1,
            "title": "Be",
            "skill_type": "grammar",
            "cefr_level": "A1",
            "lesson_status": "published",
            "lesson_id": 10,
        },
        {
            "skill_id": 2,
            "title": "Food",
            "skill_type": "vocab",
            "cefr_level": "A1",
            "lesson_status": None,
            "lesson_id": None,
        },
    ]
    out = attach_quiz_book_badges(
        rows,
        draft_by_skill={1: 3},
        published_by_skill={1: 8},
        skills_with_book={1},
    )
    assert out[0]["quiz_draft_count"] == 3
    assert out[0]["quiz_published_count"] == 8
    assert out[0]["has_book_source"] is True
    assert out[1]["quiz_draft_count"] == 0
    assert out[1]["quiz_published_count"] == 0
    assert out[1]["has_book_source"] is False


def test_learn_available_requires_flag_and_published():
    assert compute_learn_available(flag=False, has_published=True) is False
    assert compute_learn_available(flag=True, has_published=False) is False
    assert compute_learn_available(flag=True, has_published=True) is True


def test_can_skip_rules():
    assert compute_can_skip(lesson_completed=True, mastery=0.0) is True
    assert compute_can_skip(lesson_completed=False, mastery=0.7) is True
    assert compute_can_skip(lesson_completed=False, mastery=0.69) is False


def test_writing_context_from_lesson_content():
    prompt, must_use, targets, tips = writing_context_from_lesson_content(
        {
            "writing": {
                "prompt": "Write about yesterday.",
                "must_use": ["was", "were"],
            },
            "targets": [{"surface": "was"}, {"surface": "were"}],
            "form": {
                "rows": [
                    {"label": "I / he / she", "pattern": "was + verb-ing"},
                    {"label": "you / we / they", "pattern": "were + verb-ing"},
                ]
            },
        }
    )
    assert prompt.startswith("Write about")
    assert must_use == ["was", "were"]
    assert targets == ["was", "were"]
    assert tips[0].startswith("I / he / she")


def test_writing_feedback_rejects_empty(monkeypatch):
    try:
        feedback_on_writing(
            learner_text="  ",
            writing_prompt="Write",
            must_use=["hello"],
            targets=["hello"],
        )
        assert False, "expected ValueError"
    except ValueError as exc:
        assert "text" in str(exc).lower()


def test_writing_feedback_happy(monkeypatch):
    monkeypatch.setattr(
        "app.services.lesson_writing_feedback.chat_json",
        lambda system, user: {
            "corrected": "I get up at six every day.",
            "notes": ["Use get up with I, not gets up."],
            "usable": True,
        },
    )
    out = feedback_on_writing(
        learner_text="I gets up at six every day.",
        writing_prompt="Write about your routine.",
        must_use=["get up"],
        targets=["get up", "every day"],
        cefr="A1",
        form_tips=["I / he/she: get up / gets up"],
    )
    assert out["original"].startswith("I gets")
    assert "get up" in out["corrected"].lower() or out["corrected"]
    assert out["notes"]
    assert out["usable"] is True


def test_writing_feedback_marks_unusable(monkeypatch):
    monkeypatch.setattr(
        "app.services.lesson_writing_feedback.chat_json",
        lambda system, user: {
            "corrected": "At 8pm I was reading a book.",
            "notes": ["Your text is not clear. Write 1–2 sentences with was/were + -ing."],
            "usable": False,
        },
    )
    out = feedback_on_writing(
        learner_text="gagdfg",
        writing_prompt="Write about yesterday evening.",
        must_use=["was"],
        targets=["was", "were"],
        cefr="A1",
    )
    assert out["usable"] is False
    assert out["notes"]
