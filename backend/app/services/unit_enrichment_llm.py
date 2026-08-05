"""Weak-only LLM enrich for unit teaching signals."""

from __future__ import annotations

import json
from typing import Any

from app.services.llm_client import chat_json

ENRICH_SYSTEM = """You extract ESL unit teaching signals for a FIXED CEFR catalog.
Return JSON only:
{"language_focus":str|null,"grammar_cues":[str],"vocab_cues":[str],"content_summary":str|null}
Rules:
- Prefer grammar_cues slugs from catalog_skills[].slug
- Do not invent catalog skills as attach results
- Keep language_focus short
"""


def _as_str_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    out: list[str] = []
    for item in value:
        if isinstance(item, str) and item.strip():
            out.append(item.strip())
    return out


def _clip(value: str | None, max_len: int) -> str | None:
    if value is None:
        return None
    return value if len(value) <= max_len else value[:max_len]


def _normalize_payload(payload: Any) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise ValueError("LLM enrich response must be an object")
    focus = payload.get("language_focus")
    summary = payload.get("content_summary")
    return {
        "language_focus": _clip(
            focus.strip() if isinstance(focus, str) and focus.strip() else None,
            1000,
        ),
        "grammar_cues": _as_str_list(payload.get("grammar_cues")),
        "vocab_cues": _as_str_list(payload.get("vocab_cues")),
        "content_summary": _clip(
            summary.strip() if isinstance(summary, str) and summary.strip() else None,
            2000,
        ),
    }


def enrich_unit_signals_llm(
    *,
    cefr_level: str,
    book_title: str,
    unit_title: str,
    excerpt: str,
    catalog_skills: list[dict[str, Any]],
) -> dict[str, Any]:
    """Call LLM once for weak-heuristic units. Validates lightly; unknown cue labels allowed."""
    catalog_slim = [
        {"slug": s.get("slug"), "title": s.get("title")}
        for s in catalog_skills
        if s.get("slug")
    ]
    user = json.dumps(
        {
            "cefr_level": cefr_level,
            "book_title": book_title,
            "unit_title": unit_title,
            "excerpt": excerpt,
            "catalog_skills": catalog_slim,
        },
        ensure_ascii=False,
    )
    payload = chat_json(ENRICH_SYSTEM, user)
    return _normalize_payload(payload)
