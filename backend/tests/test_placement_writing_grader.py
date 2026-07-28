"""Tests for TOEIC writing grader."""

from app.services.placement.writing_grader import grade_writing_task


def test_empty_writing_scores_zero(monkeypatch):
    def boom(**kwargs):
        raise AssertionError("LLM should not be called for empty text")

    monkeypatch.setattr("app.services.placement.writing_grader.chat_json", boom)
    out = grade_writing_task(
        part="w3",
        stem="Discuss remote work",
        task_brief={},
        prompt_words=None,
        media_url=None,
        text="  ",
    )
    assert out["score"] == 0


def test_w1_clamps_score(monkeypatch):
    monkeypatch.setattr(
        "app.services.placement.writing_grader.chat_json",
        lambda system, user: {
            "grammar": 3,
            "relevance": 3,
            "score": 9,
            "ai_scores": {"grammar": 3, "relevance": 3},
            "feedback": "ok",
        },
    )
    out = grade_writing_task(
        part="w1",
        stem="s",
        task_brief=None,
        prompt_words=["a", "b"],
        media_url=None,
        text="A cat sits.",
    )
    assert out["score"] <= 3
    assert out["ai_feedback"] == "ok"
