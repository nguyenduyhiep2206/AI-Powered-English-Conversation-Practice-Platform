"""AI grade TOEIC Writing responses using ZIM-style rubrics (one batch LLM call)."""

from __future__ import annotations

from typing import Any

from app.services.llm_client import chat_json

_PART_MAX = {"w1": 3, "w2": 4, "w3": 5}

_SYSTEM = """You are a TOEIC Writing rater. Grade EACH task independently.
Return JSON only:
{"results":[{"item_id":<int>,"score":<number>,"ai_scores":{...},"feedback":"<2-4 short English sentences>"}, ...]}
Include exactly one result object per task listed, using the given item_id.
Part w1 (0-3): grammar and natural sentence; learner MUST use both prompt_words (word forms may change).
Part w2 (0-4): quality and variety of sentences, vocabulary, organization; check task_brief.
Part w3 (0-5): opinion with reasons/examples, grammar, vocabulary, organization.
Be strict but fair. Empty or off-task responses score 0. Respect each task's max_score.
"""


def _empty_result(message: str = "No response submitted.") -> dict[str, Any]:
    return {"score": 0.0, "ai_scores": {}, "ai_feedback": message}


def _clamp_score(part: str, raw: Any) -> float:
    max_score = float(_PART_MAX.get(part, 0))
    try:
        score = float(raw)
    except (TypeError, ValueError):
        score = 0.0
    return max(0.0, min(max_score, score))


def _normalize_graded(part: str, payload: dict[str, Any]) -> dict[str, Any]:
    score = _clamp_score(part, payload.get("score", 0))
    ai_scores = (
        payload.get("ai_scores") if isinstance(payload.get("ai_scores"), dict) else {}
    )
    feedback = str(payload.get("feedback") or "").strip() or "No feedback provided."
    return {"score": score, "ai_scores": ai_scores, "ai_feedback": feedback}


def grade_writing_batch(tasks: list[dict[str, Any]]) -> dict[int, dict[str, Any]]:
    """
    Grade writing tasks in one LLM call.

    Each task dict: item_id, part, stem, task_brief, prompt_words, text.
    Returns map item_id -> {score, ai_scores, ai_feedback}.
    Empty texts skip the LLM. Missing/failed LLM results score 0.
    """
    out: dict[int, dict[str, Any]] = {}
    to_grade: list[dict[str, Any]] = []

    for task in tasks:
        item_id = int(task["item_id"])
        part = str(task.get("part") or "")
        text = str(task.get("text") or "")
        if not text.strip():
            out[item_id] = _empty_result()
            continue
        if part not in _PART_MAX:
            out[item_id] = _empty_result(f"Unsupported writing part: {part}")
            continue
        to_grade.append(task)

    if not to_grade:
        return out

    batch_map = _call_batch_llm(to_grade)
    for task in to_grade:
        item_id = int(task["item_id"])
        out[item_id] = batch_map.get(item_id) or _empty_result(
            "Could not grade; please try again later."
        )
    return out


def _call_batch_llm(tasks: list[dict[str, Any]]) -> dict[int, dict[str, Any]]:
    lines = [
        f"Grade {len(tasks)} TOEIC Writing task(s). Return one result per item_id.\n"
    ]
    for task in tasks:
        part = str(task.get("part") or "")
        lines.append(
            f"---\n"
            f"item_id: {int(task['item_id'])}\n"
            f"toeic_part: {part}\n"
            f"max_score: {_PART_MAX.get(part, 0)}\n"
            f"stem: {task.get('stem') or ''}\n"
            f"task_brief: {task.get('task_brief') or {}}\n"
            f"prompt_words: {task.get('prompt_words') or []}\n"
            f"learner_text:\n{str(task.get('text') or '').strip()}\n"
        )
    user = "\n".join(lines)
    try:
        payload = chat_json(_SYSTEM, user)
    except Exception:
        try:
            payload = chat_json(_SYSTEM, user)
        except Exception:
            return {}

    if not isinstance(payload, dict):
        return {}
    rows = payload.get("results")
    if not isinstance(rows, list):
        return {}

    by_id = {int(t["item_id"]): t for t in tasks}
    out: dict[int, dict[str, Any]] = {}
    for row in rows:
        if not isinstance(row, dict):
            continue
        try:
            item_id = int(row.get("item_id"))
        except (TypeError, ValueError):
            continue
        task = by_id.get(item_id)
        if task is None:
            continue
        part = str(task.get("part") or "")
        out[item_id] = _normalize_graded(part, row)
    return out
