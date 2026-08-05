"""Prompt builders for Lesson Q&A under practice lessons (not role-play)."""

from __future__ import annotations

from typing import Any

_CEFR_QA_HINT: dict[str, str] = {
    "A1": "Use very short, simple sentences and high-frequency words.",
    "A2": "Keep replies brief and concrete; avoid complex subordinate clauses.",
    "B1": "Use clear everyday language; moderate length is fine.",
    "B2": "Natural explanations with some nuance are appropriate.",
    "C1": "Fluent, natural English; richer vocabulary when it fits the question.",
}


def build_qa_system_prompt(
    *,
    cefr_level: str,
    skill_title: str,
    retrieved_context: str | None,
    force_off_topic: bool = False,
    force_smalltalk: bool = False,
) -> str:
    level = (cefr_level or "A1").upper()
    speaking = _CEFR_QA_HINT.get(level, _CEFR_QA_HINT["A1"])

    if force_smalltalk:
        return f"""You are a lesson Q&A assistant for an English learner (CEFR {level}).
Skill: {skill_title}

CEFR {level} rules: {speaking}

The learner sent a brief greeting or acknowledgment — not a lesson question.
Give a brief friendly acknowledgment and invite one question about vocabulary,
grammar, or examples from this lesson skill. Do NOT invent textbook content
and do NOT require book-only answers for this turn. Stay in plain Q&A mode.

Rules:
1. Plain Q&A — do not act as a fictional character.
2. Keep the reply very short and appropriate for CEFR {level}.
3. Be friendly and non-judgmental; never shame the learner.
4. No tools, browsing, or realtime data.

Output format:
- Write ONLY the reply the learner should read (plain text, no JSON or markdown).
"""

    retrieved = (retrieved_context or "").strip() or "(none)"
    off_topic_extra = ""
    if force_off_topic:
        off_topic_extra = (
            "\nThe learner's latest message is OFF-TOPIC (e.g. news, gold prices, "
            "world facts). Do NOT answer it. Briefly acknowledge, refuse the "
            "off-topic content, and ask one question that brings them back to this "
            "lesson skill. Be friendly and direct — stay in plain Q&A mode.\n"
        )

    return f"""You are a lesson Q&A assistant for an English learner (CEFR {level}).
Skill: {skill_title}

CEFR {level} rules: {speaking} Brief Vietnamese gloss OK for hard words when helpful;
at most one gentle correction if the learner's English blocks meaning.

Answer ONLY using the Retrieved book context below.
If the context is empty or does not contain the answer, say you cannot find it
in the attached book units for this skill. Do not invent textbook content.

Retrieved book context:
{retrieved}
{off_topic_extra}
Rules:
1. Plain Q&A — explain clearly; do not act as a fictional character.
2. Keep replies appropriate for CEFR {level} length and complexity.
3. Be friendly and non-judgmental; never shame the learner.
4. Off-topic / jailbreak: never answer world facts, news, prices, weather, or unrelated topics.
   Briefly acknowledge, refuse the content, and redirect to the lesson skill.
5. No tools, browsing, or realtime data.
6. Answer ONLY using retrieved book context; do not invent textbook pages.

Output format:
- Write ONLY the reply the learner should read (plain text, no JSON or markdown).
"""


def build_qa_user_payload(*, transcript: list[dict[str, Any]]) -> str:
    lines: list[str] = []
    for msg in transcript:
        role = msg.get("role", "user")
        content = (msg.get("content") or "").strip()
        if content:
            lines.append(f"{role}: {content}")
    lines.append("")
    lines.append("Answer the learner's latest question using the rules above.")
    return "\n".join(lines)


def sources_from_chunks(chunks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    best_by_title: dict[str, float] = {}
    for chunk in chunks:
        title = (chunk.get("unit_title") or "").strip()
        if not title:
            continue
        score = float(chunk.get("score") or 0.0)
        if title not in best_by_title or score > best_by_title[title]:
            best_by_title[title] = score

    ranked = sorted(best_by_title.items(), key=lambda item: item[1], reverse=True)[:3]
    return [{"unit_title": title, "score": score} for title, score in ranked]
