from app.services.lesson_service import compute_can_skip, compute_learn_available
from app.services.lesson_writing_feedback import feedback_on_writing


def test_learn_available_requires_flag_and_published():
    assert compute_learn_available(flag=False, has_published=True) is False
    assert compute_learn_available(flag=True, has_published=False) is False
    assert compute_learn_available(flag=True, has_published=True) is True


def test_can_skip_rules():
    assert compute_can_skip(lesson_completed=True, mastery=0.0) is True
    assert compute_can_skip(lesson_completed=False, mastery=0.7) is True
    assert compute_can_skip(lesson_completed=False, mastery=0.69) is False


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
        },
    )
    out = feedback_on_writing(
        learner_text="I gets up at six every day.",
        writing_prompt="Write about your routine.",
        must_use=["get up"],
        targets=["get up", "every day"],
        cefr="A1",
    )
    assert out["original"].startswith("I gets")
    assert "get up" in out["corrected"].lower() or out["corrected"]
    assert out["notes"]
