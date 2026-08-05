"""RAG helpers and off-topic gating for AI Tutor."""

from __future__ import annotations

import math
import re
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.book_skill_source import BookSkillSourceDB
from app.services.embedding_service import embed_texts

_OFF_TOPIC_RE = re.compile(
    r"("
    r"gi[aá]\s*v[aà]ng|gold\s*price|ch[uứ]ng\s*kho[aá]n|stock\s*market|"
    r"bitcoin|crypto|th[oờ]i\s*ti[eế]t|weather\s*today|"
    r"tin\s*t[uứ]c|breaking\s*news|who\s+is\s+the\s+president|"
    r"t[oổ]ng\s*th[oố]ng|lottery|x[oổ]\s*s[oố]"
    r")",
    re.I,
)

_RAG_HINT_RE = re.compile(
    r"("
    r"\?|explain|what\s+does|what\s+is|how\s+do\s+i|meaning|"
    r"grammar|vocabulary|why\s+do\s+we|theo\s*s[aá]ch|"
    r"gi[aả]i\s*th[ií]ch|ngh[iĩ]a\s*l[aà]|c[aá]ch\s*d[uù]ng"
    r")",
    re.I,
)


def is_off_topic(text: str) -> bool:
    t = (text or "").strip()
    if not t:
        return False
    return bool(_OFF_TOPIC_RE.search(t))


def needs_rag(text: str) -> bool:
    if settings.TUTOR_RAG_ALWAYS_LIGHT:
        return True
    t = (text or "").strip()
    if len(t) < 8:
        return False
    return bool(_RAG_HINT_RE.search(t))


def cosine(a: list[float], b: list[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = 0.0
    na = 0.0
    nb = 0.0
    for x, y in zip(a, b):
        dot += x * y
        na += x * x
        nb += y * y
    if na <= 0 or nb <= 0:
        return 0.0
    return float(dot / (math.sqrt(na) * math.sqrt(nb)))


def select_top_chunks(
    query_vec: list[float],
    docs: list[dict[str, Any]],
    *,
    top_k: int,
    min_score: float,
    max_chars: int,
) -> list[dict[str, Any]]:
    scored: list[tuple[float, dict[str, Any]]] = []
    for doc in docs:
        emb = doc.get("embedding")
        if not isinstance(emb, list) or not emb:
            continue
        score = cosine(query_vec, [float(x) for x in emb])
        if score >= min_score:
            scored.append((score, doc))
    scored.sort(key=lambda x: x[0], reverse=True)

    out: list[dict[str, Any]] = []
    used = 0
    for score, doc in scored[: max(1, top_k) * 3]:
        text = str(doc.get("text") or doc.get("embedded_text") or "").strip()
        if not text:
            continue
        piece = text if used + len(text) <= max_chars else text[: max(0, max_chars - used)]
        if not piece:
            break
        out.append(
            {
                "score": round(score, 4),
                "text": piece,
                "book_id": doc.get("book_id"),
                "unit_id": doc.get("unit_id"),
                "chunk_id": str(doc.get("_id") or doc.get("chunk_id") or ""),
                "unit_title": doc.get("unit_title"),
            }
        )
        used += len(piece)
        if len(out) >= top_k or used >= max_chars:
            break
    return out


def format_retrieved_block(chunks: list[dict[str, Any]]) -> str:
    if not chunks:
        return "(none)"
    parts: list[str] = []
    for i, c in enumerate(chunks, start=1):
        title = c.get("unit_title") or "unit"
        parts.append(f"[{i}] ({title}, score={c.get('score')})\n{c.get('text', '')}")
    return "\n\n".join(parts)


async def resolve_unit_scope(
    db: AsyncSession, skill_ids: list[int]
) -> list[tuple[int, int]]:
    if not skill_ids:
        return []
    rows = (
        await db.execute(
            select(BookSkillSourceDB.book_id, BookSkillSourceDB.unit_id)
            .where(
                BookSkillSourceDB.skill_id.in_(skill_ids),
                BookSkillSourceDB.is_excluded.is_(False),
            )
            .order_by(BookSkillSourceDB.is_primary.desc(), BookSkillSourceDB.id)
        )
    ).all()
    seen: set[tuple[int, int]] = set()
    out: list[tuple[int, int]] = []
    for book_id, unit_id in rows:
        key = (int(book_id), int(unit_id))
        if key not in seen:
            seen.add(key)
            out.append(key)
    return out


def load_embedded_chunks(scope: list[tuple[int, int]], *, limit_per_unit: int = 40) -> list[dict]:
    if not scope or not settings.MONGODB_URL:
        return []
    from app.services.book_chunk_service import EMBED_STATUS_EMBEDDED, _sync_collection

    client, collection = _sync_collection()
    try:
        docs: list[dict] = []
        for book_id, unit_id in scope:
            cursor = (
                collection.find(
                    {
                        "book_id": int(book_id),
                        "unit_id": int(unit_id),
                        "embed_status": EMBED_STATUS_EMBEDDED,
                        "embedding": {"$type": "array"},
                    },
                    {
                        "text": 1,
                        "embedded_text": 1,
                        "embedding": 1,
                        "book_id": 1,
                        "unit_id": 1,
                        "unit_title": 1,
                    },
                )
                .sort([("chunk_index", 1)])
                .limit(limit_per_unit)
            )
            docs.extend(list(cursor))
        return docs
    finally:
        client.close()


async def retrieve_for_session(
    db: AsyncSession,
    *,
    skill_ids: list[int],
    query: str,
    enabled: bool | None = None,
) -> list[dict[str, Any]]:
    if not (settings.TUTOR_RAG_ENABLED if enabled is None else enabled):
        return []
    if not skill_ids and not settings.TUTOR_RAG_CATALOG_LEVEL_FALLBACK:
        return []
    scope = await resolve_unit_scope(db, skill_ids)
    if not scope:
        return []
    docs = load_embedded_chunks(scope)
    if not docs:
        return []
    vectors = embed_texts([query.strip()])
    if not vectors:
        return []
    return select_top_chunks(
        vectors[0],
        docs,
        top_k=settings.TUTOR_RAG_TOP_K,
        min_score=settings.TUTOR_RAG_MIN_SCORE,
        max_chars=settings.TUTOR_RAG_MAX_CHARS,
    )
