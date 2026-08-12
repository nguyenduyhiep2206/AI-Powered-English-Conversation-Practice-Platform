"""Tests for TOEIC writing grader."""

from app.services.placement.writing_grader import grade_writing_batch


def test_empty_writing_scores_zero(monkeypatch):
    def boom(*_a, **_k):
        raise AssertionError("LLM should not be called for empty text")

    monkeypatch.setattr("app.services.placement.writing_grader.chat_json", boom)
    out = grade_writing_batch(
        [
            {
                "item_id": 1,
                "part": "w3",
                "stem": "Discuss remote work",
                "task_brief": {},
                "prompt_words": None,
                "text": "  ",
            }
        ]
    )
    assert out[1]["score"] == 0


def test_batch_clamps_w1_score(monkeypatch):
    monkeypatch.setattr(
        "app.services.placement.writing_grader.chat_json",
        lambda system, user: {
            "results": [
                {
                    "item_id": 1,
                    "score": 9,
                    "ai_scores": {"grammar": 3},
                    "feedback": "ok",
                }
            ]
        },
    )
    out = grade_writing_batch(
        [
            {
                "item_id": 1,
                "part": "w1",
                "stem": "s",
                "task_brief": None,
                "prompt_words": ["a", "b"],
                "text": "A cat sits.",
            }
        ]
    )
    assert out[1]["score"] <= 3
    assert out[1]["ai_feedback"] == "ok"


def test_batch_grades_once(monkeypatch):
    calls: list[str] = []

    def fake_chat(system: str, user: str):
        calls.append(system)
        return {
            "results": [
                {
                    "item_id": 1,
                    "score": 2,
                    "ai_scores": {"grammar": 2},
                    "feedback": "ok1",
                },
                {
                    "item_id": 2,
                    "score": 3,
                    "ai_scores": {"org": 3},
                    "feedback": "ok2",
                },
            ]
        }

    monkeypatch.setattr(
        "app.services.placement.writing_grader.chat_json", fake_chat
    )
    out = grade_writing_batch(
        [
            {
                "item_id": 1,
                "part": "w1",
                "stem": "s1",
                "task_brief": None,
                "prompt_words": ["a", "b"],
                "text": "Hello world",
            },
            {
                "item_id": 2,
                "part": "w2",
                "stem": "s2",
                "task_brief": {},
                "prompt_words": None,
                "text": "Dear team,...",
            },
            {
                "item_id": 3,
                "part": "w3",
                "stem": "s3",
                "task_brief": {},
                "prompt_words": None,
                "text": "   ",
            },
        ]
    )
    assert len(calls) == 1
    assert out[1]["score"] == 2
    assert out[2]["score"] == 3
    assert out[3]["score"] == 0


def test_batch_failure_scores_zero(monkeypatch):
    def fake_chat(system: str, user: str):
        raise RuntimeError("llm down")

    monkeypatch.setattr(
        "app.services.placement.writing_grader.chat_json", fake_chat
    )
    out = grade_writing_batch(
        [
            {
                "item_id": 10,
                "part": "w1",
                "stem": "s",
                "task_brief": None,
                "prompt_words": ["a", "b"],
                "text": "A sentence.",
            }
        ]
    )
    assert out[10]["score"] == 0
    assert "Could not grade" in out[10]["ai_feedback"]
