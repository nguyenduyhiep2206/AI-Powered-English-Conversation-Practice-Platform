"""AI grade TOEIC Writing responses using ZIM-style rubrics."""

from __future__ import annotations

from typing import Any

from app.services.llm_client import chat_json

_PART_MAX = {"w1": 3, "w2": 4, "w3": 5}

_SYSTEM = """You are a TOEIC Writing rater. Score holistically using the official-style criteria.
Return JSON only with keys: score (number), ai_scores (object of criterion→number), feedback (2-4 short English sentences).
Part w1 (0-3): grammar, relevance to the picture (and use of prompt words when given).
Part w2 (0-4): quality and variety of sentences, vocabulary, organization; check task_brief constraints.
Part w3 (0-5): opinion supported with reasons/examples, grammar, vocabulary, organization.
Be strict but fair. Empty or off-task responses score 0.
"""


def grade_writing_task(
    *,
    part: str,
    stem: str,
    task_brief: dict[str, Any] | None,
    prompt_words: list[str] | None,
    media_url: str | None,
    text: str,
) -> dict[str, Any]:
    cleaned = (text or "").strip()
    if not cleaned:
        return {
            "score": 0.0,
            "ai_scores": {},
            "ai_feedback": "No response submitted.",
        }
    if part not in _PART_MAX:
        return {
            "score": 0.0,
            "ai_scores": {},
            "ai_feedback": f"Unsupported writing part: {part}",
        }

    user = (
        f"toeic_part: {part}\n"
        f"max_score: {_PART_MAX[part]}\n"
        f"stem: {stem}\n"
        f"task_brief: {task_brief or {}}\n"
        f"prompt_words: {prompt_words or []}\n"
        f"media_url: {media_url or ''}\n"
        f"learner_text:\n{cleaned}\n"
    )
    try:
        payload = chat_json(_SYSTEM, user)
    except Exception:
        try:
            payload = chat_json(_SYSTEM, user)
        except Exception:
            return {
                "score": 0.0,
                "ai_scores": {},
                "ai_feedback": "Could not grade; try retake later.",
            }

    if not isinstance(payload, dict):
        return {
            "score": 0.0,
            "ai_scores": {},
            "ai_feedback": "Could not grade; try retake later.",
        }

    max_score = _PART_MAX[part]
    raw_score = payload.get("score", 0)
    try:
        score = float(raw_score)
    except (TypeError, ValueError):
        score = 0.0
    score = max(0.0, min(float(max_score), score))
    ai_scores = payload.get("ai_scores") if isinstance(payload.get("ai_scores"), dict) else {}
    feedback = str(payload.get("feedback") or "").strip() or "No feedback provided."
    return {"score": score, "ai_scores": ai_scores, "ai_feedback": feedback}
