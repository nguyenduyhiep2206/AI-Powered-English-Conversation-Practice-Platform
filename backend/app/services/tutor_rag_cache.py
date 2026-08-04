"""Redis cache for tutor RAG retrieval payloads."""

from __future__ import annotations

import hashlib
import json
from typing import Any

from app.core.config import settings
from app.core.redis import redis_client


def normalize_query(query: str) -> str:
    return " ".join((query or "").strip().lower().split())


def cache_key(normalized_query: str, skill_ids: list[int]) -> str:
    skills = ",".join(str(int(s)) for s in sorted(set(skill_ids)))
    raw = f"{normalized_query}|{skills}"
    digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()[:32]
    return f"tutor:rag:{digest}"


async def cache_get(key: str) -> dict[str, Any] | None:
    try:
        raw = await redis_client.get(key)
    except Exception:
        return None
    if not raw:
        return None
    try:
        if isinstance(raw, bytes):
            raw = raw.decode("utf-8")
        data = json.loads(raw)
        return data if isinstance(data, dict) else None
    except Exception:
        return None


async def cache_set(key: str, value: dict[str, Any], ttl: int | None = None) -> None:
    seconds = int(ttl if ttl is not None else settings.TUTOR_RAG_CACHE_TTL_SECONDS)
    try:
        await redis_client.set(key, json.dumps(value, ensure_ascii=False), ex=max(1, seconds))
    except Exception:
        return
