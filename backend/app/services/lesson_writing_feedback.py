"""Serve-time AI feedback for mini-unit writing (not mastery)."""

from __future__ import annotations

from typing import Any

from app.services.llm_client import chat_json

_SYSTEM = """You coach an ESL learner after a short writing task in a mini-unit.
Teach in English only (English→English). Do NOT use Vietnamese.

Learner CEFR level: {cefr}
Write feedback notes in simple English a {cefr} learner can understand.

Return JSON only:
{{
  "corrected": "improved English version of the learner text",
  "notes": ["short English note 1", "short English note 2"]
}}
Rules:
- Keep the learner's meaning.
- Prefer natural English.
- If must_use phrases are missing, mention them in notes and weave them into corrected when fitting.
- Notes: 1-4 short English bullets at {cefr} difficulty.
- Do not invent long essays; stay close to the original length.
"""


def feedback_on_writing(
    *,
    learner_text: str,
    writing_prompt: str,
    must_use: list[str] | None,
    targets: list[str] | None,
    cefr: str = "A1",
) -> dict[str, Any]:
    cleaned = (learner_text or "").strip()
    if not cleaned:
        raise ValueError("text is required")

    user = (
        f"cefr: {cefr}\n"
        f"writing_prompt: {writing_prompt}\n"
        f"must_use: {must_use or []}\n"
        f"targets: {targets or []}\n"
        f"learner_text:\n{cleaned}\n"
    )
    system = _SYSTEM.format(cefr=cefr or "A1")
    try:
        payload = chat_json(system, user)
    except Exception:
        try:
            payload = chat_json(system, user)
        except Exception as exc:
            raise RuntimeError("Could not generate writing feedback") from exc

    if not isinstance(payload, dict):
        raise RuntimeError("Could not generate writing feedback")

    corrected = str(payload.get("corrected") or "").strip() or cleaned
    notes_raw = payload.get("notes")
    notes: list[str] = []
    if isinstance(notes_raw, list):
        notes = [str(n).strip() for n in notes_raw if str(n).strip()][:4]

    return {
        "original": cleaned,
        "corrected": corrected,
        "notes": notes,
    }
