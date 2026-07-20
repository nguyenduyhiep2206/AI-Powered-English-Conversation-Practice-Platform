"""LLM refine for skill graph sync (one batch call per book)."""

from __future__ import annotations

import json
from typing import Any

from app.models.enums import SkillTypeEnum
from app.services.llm_client import chat_json
from app.services.skill_graph_validate import validate_llm_graph_payload

SYSTEM_PROMPT = """You are an ESL curriculum graph assistant.
Map book units to canonical learning skills for ONE CEFR level.
Prefer reusing existing_skills slugs when the unit teaches the same skill.
Return JSON only:
{
  "unit_mappings":[
    {"unit_index":int,"slug":str,"title":str,"skill_type":"grammar|vocabulary|reading|functional",
     "difficulty_in_level":1-10,"exclude":bool}
  ],
  "prerequisites":[{"from_slug":str,"to_slug":str}]
}
Rules:
- One mapping per unit_index; slug snake_case [a-z0-9_]{2,120}
- difficulty_in_level: 1=start of level, 10=end of level
- exclude=true for answer keys / index / non-teaching units
- prerequisites: from must be learned before to; only use slugs in mappings or existing_skills
- Do not invent CEFR levels; stay within the given level's skills
"""


def refine_units_with_llm(
    *,
    cefr_level: str,
    book_title: str,
    existing_skills: list[dict[str, Any]],
    units: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[tuple[str, str]]]:
    """Call LLM once, then validate. Raises on bad/unusable responses (caller falls back)."""
    user = json.dumps(
        {
            "cefr_level": cefr_level,
            "book_title": book_title,
            "existing_skills": existing_skills,
            "units": units,
        },
        ensure_ascii=False,
    )
    payload = chat_json(SYSTEM_PROMPT, user)
    if not isinstance(payload, dict):
        raise ValueError("LLM skill graph response must be an object")
    allowed = {e.value for e in SkillTypeEnum}
    return validate_llm_graph_payload(
        payload,
        unit_indexes={int(u["unit_index"]) for u in units},
        existing_slugs={str(s["slug"]) for s in existing_skills},
        allowed_skill_types=allowed,
    )
