"""Redis cache key helper for Lesson Q&A RAG retrieval payloads."""

from __future__ import annotations

import hashlib

from app.services.tutor_rag_cache import cache_get, cache_set, normalize_query

__all__ = ["cache_get", "cache_key", "cache_set", "normalize_query"]


def cache_key(
    normalized_query: str,
    skill_ids: list[int],
    *,
    scope: list[tuple[int, int]] | None = None,
) -> str:
    """Include unit scope so re-attaching a skill busts stale RAG payloads."""
    skills = ",".join(str(int(s)) for s in sorted(set(skill_ids)))
    if scope:
        scope_part = ",".join(f"{int(b)}:{int(u)}" for b, u in sorted(set(scope)))
    else:
        scope_part = "-"
    raw = f"{normalized_query}|{skills}|{scope_part}"
    digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()[:32]
    return f"lesson_qa:rag:{digest}"
