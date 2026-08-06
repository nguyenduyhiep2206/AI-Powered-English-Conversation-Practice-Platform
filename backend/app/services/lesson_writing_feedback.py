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
  "corrected": "improved English version OR a short model answer if the attempt is not usable",
  "notes": ["short English note 1", "short English note 2"],
  "usable": true
}}
Rules:
- Respond to THIS learner_text. Do not ignore it.
- usable=false when the text is empty of meaning, random letters, or not a real English attempt.
  Then: corrected = one short model answer that fits writing_prompt + must_use;
  notes must say the attempt is not clear and what to write (1–2 concrete tips).
- usable=true when there is a real attempt: keep the learner's meaning; fix grammar gently;
  weave in missing must_use only when natural.
- Prefer 1–3 notes that react to mistakes in THEIR text (or missing must_use).
- You may use form_tips as a brief reminder (at most one note), not dump the whole grammar table.
- Do not invent long essays; stay close to the original length when usable=true.
"""


def form_tips_from_lesson_content(content: dict[str, Any] | None) -> list[str]:
    """Extract short form reminders from lesson content.form.rows."""
    if not isinstance(content, dict):
        return []
    form = content.get("form") if isinstance(content.get("form"), dict) else {}
    rows = form.get("rows") if isinstance(form.get("rows"), list) else []
    tips: list[str] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        label = str(row.get("label") or "").strip()
        pattern = str(row.get("pattern") or "").strip()
        if label and pattern:
            tips.append(f"{label}: {pattern}")
        elif pattern:
            tips.append(pattern)
    return tips[:6]


def writing_context_from_lesson_content(
    content: dict[str, Any] | None,
) -> tuple[str, list[str], list[str], list[str]]:
    """Return (writing_prompt, must_use, target_surfaces, form_tips)."""
    if not isinstance(content, dict):
        return "", [], [], []
    writing = content.get("writing") if isinstance(content.get("writing"), dict) else {}
    prompt = str(writing.get("prompt") or "")
    must_raw = (
        writing.get("must_use") if isinstance(writing.get("must_use"), list) else []
    )
    must_use = [str(x) for x in must_raw if str(x).strip()]
    targets = content.get("targets") if isinstance(content.get("targets"), list) else []
    target_surfaces = [
        str(t.get("surface") or "").strip()
        for t in targets
        if isinstance(t, dict) and str(t.get("surface") or "").strip()
    ]
    return prompt, must_use, target_surfaces, form_tips_from_lesson_content(content)


def feedback_on_writing(
    *,
    learner_text: str,
    writing_prompt: str,
    must_use: list[str] | None,
    targets: list[str] | None,
    cefr: str = "A1",
    form_tips: list[str] | None = None,
) -> dict[str, Any]:
    cleaned = (learner_text or "").strip()
    if not cleaned:
        raise ValueError("text is required")
    tips = [str(t).strip() for t in (form_tips or []) if str(t).strip()][:6]
    payload = _request_feedback_payload(
        cleaned=cleaned,
        writing_prompt=writing_prompt,
        must_use=must_use,
        targets=targets,
        cefr=cefr,
        tips=tips,
    )
    return _normalize_feedback_payload(payload, cleaned=cleaned)


def _request_feedback_payload(
    *,
    cleaned: str,
    writing_prompt: str,
    must_use: list[str] | None,
    targets: list[str] | None,
    cefr: str,
    tips: list[str],
) -> dict[str, Any]:
    user = (
        f"cefr: {cefr}\n"
        f"writing_prompt: {writing_prompt}\n"
        f"must_use: {must_use or []}\n"
        f"targets: {targets or []}\n"
        f"form_tips: {tips}\n"
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
    return payload


def _normalize_feedback_payload(
    payload: dict[str, Any], *, cleaned: str
) -> dict[str, Any]:
    corrected = str(payload.get("corrected") or "").strip() or cleaned
    notes_raw = payload.get("notes")
    notes: list[str] = []
    if isinstance(notes_raw, list):
        notes = [str(n).strip() for n in notes_raw if str(n).strip()][:4]
    usable = payload.get("usable")
    if usable is None:
        usable = True
    return {
        "original": cleaned,
        "corrected": corrected,
        "notes": notes,
        "usable": bool(usable),
    }
