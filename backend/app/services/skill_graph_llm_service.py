"""LLM attach: map book units onto a fixed CEFR catalog (no invent slugs)."""

from __future__ import annotations

import json
from typing import Any

from app.services.llm_client import chat_json
from app.services.skill_graph_validate import validate_llm_attach_payload

ATTACH_SYSTEM_PROMPT = """You map ESL book units onto a FIXED catalog of skills for one CEFR level.
Return JSON only:
{"unit_mappings":[{"unit_index":int,"slug":str|null,"exclude":bool}]}
Rules:
- slug MUST be one of catalog_skills[].slug, or null if no good match
- exclude=true for review/test/index/answer key units (slug may be null)
- Do not invent slugs. Do not return prerequisites.
- Prefer the closest pedagogical match; one unit → at most one skill
- When title is thematic (topic/theme, not a grammar name), prefer grammar_cues / language_focus over the title alone
- Fields shown (title, language_focus, grammar_cues, vocab_cues, content_summary) are sufficient — never require raw page text
- Still at most one slug per unit; never invent catalog slugs
"""


def attach_units_with_llm(
    *,
    cefr_level: str,
    book_title: str,
    catalog_skills: list[dict[str, Any]],
    units: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Call LLM once, then validate. Raises on bad/unusable responses (caller falls back)."""
    user = json.dumps(
        {
            "cefr_level": cefr_level,
            "book_title": book_title,
            "catalog_skills": catalog_skills,
            "units": units,
        },
        ensure_ascii=False,
    )
    payload = chat_json(ATTACH_SYSTEM_PROMPT, user)
    if not isinstance(payload, dict):
        raise ValueError("LLM skill graph response must be an object")
    return validate_llm_attach_payload(
        payload,
        unit_indexes={int(u["unit_index"]) for u in units},
        catalog_slugs={str(s["slug"]) for s in catalog_skills},
    )
