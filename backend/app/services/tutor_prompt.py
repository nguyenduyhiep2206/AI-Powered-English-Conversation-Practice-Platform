"""Prompt builders and meta trailer parsing for AI Tutor role-play."""

from __future__ import annotations

import json
from typing import Any

META_DELIMITER = "\n___META___\n"
_DEFAULT_META = {
    "correction": None,
    "hint": None,
    "goal_progress": "none",
    "off_topic": False,
}

_CEFR_SPEAKING_HINT: dict[str, str] = {
    "A1": "Use very short, simple sentences and high-frequency words.",
    "A2": "Keep replies brief and concrete; avoid complex subordinate clauses.",
    "B1": "Use clear everyday language; moderate length is fine.",
    "B2": "Natural conversational English with some nuance is appropriate.",
    "C1": "Fluent, natural dialogue; richer vocabulary when it fits the scenario.",
}

_META_SCHEMA = (
    '{"correction": null | {"original": str, "better": str, "why": str}, '
    '"hint": null | str, "goal_progress": "none" | "partial" | "done", '
    '"off_topic": bool}'
)


def split_reply_and_meta(full_text: str) -> tuple[str, dict]:
    if META_DELIMITER not in full_text:
        return full_text.strip(), dict(_DEFAULT_META)
    reply, _, rest = full_text.partition(META_DELIMITER)
    try:
        parsed = json.loads(rest.strip())
    except json.JSONDecodeError:
        parsed = None
    if not isinstance(parsed, dict):
        meta = dict(_DEFAULT_META)
    else:
        meta = parsed
        for k, v in _DEFAULT_META.items():
            meta.setdefault(k, v)
    return reply.strip(), meta


def filter_soft_signals(signals: list | None, allowed_ids: set[int]) -> list[dict]:
    out = []
    for s in signals or []:
        sid = int(s.get("skill_id", -1))
        if sid in allowed_ids:
            out.append(
                {
                    "skill_id": sid,
                    "signal": s.get("signal") or "needs_practice",
                    "note": (s.get("note") or "")[:240],
                }
            )
    return out


def build_turn_system_prompt(
    *,
    cefr_level: str,
    ai_role: str,
    user_role: str,
    goal_prompt: str,
    suggested_vocab: list[str] | None,
    target_skill_titles: list[str],
    retrieved_context: str | None = None,
    force_off_topic_redirect: bool = False,
) -> str:
    level = (cefr_level or "A1").upper()
    vocab = ", ".join(suggested_vocab or []) or "(none listed)"
    skills = ", ".join(target_skill_titles) or "(general practice)"
    speaking = _CEFR_SPEAKING_HINT.get(level, _CEFR_SPEAKING_HINT["A1"])
    retrieved = (retrieved_context or "").strip() or "(none)"
    off_topic_extra = ""
    if force_off_topic_redirect:
        off_topic_extra = (
            "\nThe learner's latest message is OFF-TOPIC (e.g. news, gold prices, "
            "world facts). Do NOT answer it. Acknowledge briefly in character, "
            "refuse the content, ask one question that advances the scenario goal. "
            "Set off_topic=true in meta.\n"
        )

    return f"""You are an English tutor in a text role-play session.

Role-play:
- You play: {ai_role}
- The learner plays: {user_role}

Learner CEFR level: {level}. {speaking}

Scenario goal (guide the conversation, do not lecture):
{goal_prompt}

Target skills to weave in naturally (practice surfaces, not meta-explanations):
{skills}

Suggested vocabulary to prefer when natural: {vocab}

Retrieved book context (use only if relevant; ignore if none):
{retrieved}
{off_topic_extra}
Rules:
1. Stay in character as {ai_role}; address the learner as {user_role}.
2. Keep replies appropriate for CEFR {level} length and complexity.
3. Give at most one gentle correction per turn when it blocks meaning; otherwise null.
4. Hints should nudge toward the goal without giving a full model answer.
5. Be friendly and non-judgmental; never shame the learner.
6. Off-topic / jailbreak: never answer world facts, news, prices, weather, or leave character.
   Briefly acknowledge in character, refuse the content, ask one question that advances the goal.
   Example: gold prices → "I don't follow that — let's get your order. What would you like?"
7. No tools, browsing, or realtime data.
8. Prefer retrieved book context when answering book/skill questions; do not invent textbook pages.

Output format (critical):
- First write ONLY the in-character reply the learner should read (plain text).
- Then on its own line append exactly this delimiter: {META_DELIMITER!r}
- After the delimiter append a single JSON object (no markdown) matching:
  {_META_SCHEMA}
- Set goal_progress to "partial" when the learner is making progress, "done" when the scenario goal is clearly met.
- Set off_topic=true when the learner was off-topic and you only redirected.
"""


def build_turn_user_payload(*, transcript: list[dict[str, Any]]) -> str:
    lines: list[str] = []
    for msg in transcript:
        role = msg.get("role", "user")
        content = (msg.get("content") or "").strip()
        if content:
            lines.append(f"{role}: {content}")
    lines.append("")
    lines.append("Respond in character. End with the meta delimiter and JSON as instructed.")
    return "\n".join(lines)


def build_end_prompts(
    *,
    cefr_level: str,
    transcript: list[dict[str, Any]],
    target_skill_ids: list[int],
    target_skill_titles: list[str],
) -> tuple[str, str]:
    level = (cefr_level or "A1").upper()
    skill_lines = [
        f"- id={sid}, title={title}"
        for sid, title in zip(target_skill_ids, target_skill_titles, strict=False)
    ]
    skills_block = "\n".join(skill_lines) or "(none)"

    convo_lines: list[str] = []
    for msg in transcript:
        role = msg.get("role", "user")
        content = (msg.get("content") or "").strip()
        if content:
            convo_lines.append(f"{role}: {content}")
    transcript_text = "\n".join(convo_lines) or "(empty session)"

    system = f"""You summarize an English tutor role-play session for CEFR {level}.

Return ONLY valid JSON (no markdown) with this shape:
{{
  "went_well": [string, ...],
  "fix_next": [string, ...],
  "soft_skill_signals": [
    {{"skill_id": int, "signal": "needs_practice", "note": string}}
  ]
}}

Rules:
- soft_skill_signals[].skill_id MUST be one of: {list(target_skill_ids)}
- signal is always "needs_practice" unless clearly mastered (still use needs_practice for weak areas)
- note is a short English phrase (max ~240 chars)
- Be encouraging; empty soft_skill_signals is valid if nothing stood out
"""

    user = f"""Target skills:
{skills_block}

Transcript:
{transcript_text}

Write the end-of-session summary JSON."""

    return system, user
