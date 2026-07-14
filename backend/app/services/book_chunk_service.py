"""MongoDB book_chunks persistence for RAG indexing."""

from __future__ import annotations

import logging
from typing import Any

from app.core.config import settings
from app.core.mongodb import get_mongo_db

logger = logging.getLogger(__name__)

BOOK_CHUNKS_COLLECTION = "book_chunks"
EMBED_STATUS_PENDING = "pending"
EMBED_STATUS_EMBEDDED = "embedded"
EMBED_STATUS_FAILED = "failed"



def _sync_collection():
    """Sync pymongo collection (background workers / delete path)."""
    if not settings.MONGODB_URL:
        raise RuntimeError("MONGODB_URL is not configured")

    from pymongo import MongoClient

    client = MongoClient(settings.MONGODB_URL)
    db = client[settings.MONGODB_DB_NAME]
    return client, db[BOOK_CHUNKS_COLLECTION]


def ensure_book_chunks_indexes() -> None:
    if not settings.MONGODB_URL:
        return
    client, collection = _sync_collection()
    try:
        collection.create_index(
            [("book_id", 1), ("unit_id", 1)],
            name="book_unit_idx",
        )
        collection.create_index([("book_id", 1)], name="book_id_idx")
        collection.create_index(
            [("book_id", 1), ("embed_status", 1)],
            name="book_embed_status_idx",
        )
    finally:
        client.close()


def delete_book_chunks(book_id: int) -> int:
    if not settings.MONGODB_URL:
        return 0

    try:
        from pymongo import MongoClient
    except ImportError:
        return 0

    client = MongoClient(settings.MONGODB_URL)
    try:
        db = client[settings.MONGODB_DB_NAME]
        result = db[BOOK_CHUNKS_COLLECTION].delete_many({"book_id": book_id})
        return int(result.deleted_count)
    finally:
        client.close()


def delete_unit_chunks(book_id: int, unit_id: int) -> int:
    if not settings.MONGODB_URL:
        return 0

    client, collection = _sync_collection()
    try:
        result = collection.delete_many({"book_id": book_id, "unit_id": unit_id})
        return int(result.deleted_count)
    finally:
        client.close()


def insert_chunks(documents: list[dict[str, Any]]) -> int:
    if not documents:
        return 0
    if not settings.MONGODB_URL:
        raise RuntimeError("MONGODB_URL is not configured")

    client, collection = _sync_collection()
    try:
        result = collection.insert_many(documents)
        return len(result.inserted_ids)
    finally:
        client.close()


def count_book_chunks(book_id: int) -> int:
    if not settings.MONGODB_URL:
        return 0
    client, collection = _sync_collection()
    try:
        return int(collection.count_documents({"book_id": book_id}))
    finally:
        client.close()


def fetch_pending_embed_chunks(
    book_id: int,
    *,
    unit_id: int | None = None,
    limit: int = 32,
) -> list[dict[str, Any]]:
    """Return chunks waiting for Voyage embeddings (text already saved)."""
    if not settings.MONGODB_URL:
        return []

    query: dict[str, Any] = {
        "book_id": int(book_id),
        "embed_status": {"$in": [EMBED_STATUS_PENDING, EMBED_STATUS_FAILED]},
    }
    if unit_id is not None:
        query["unit_id"] = int(unit_id)

    client, collection = _sync_collection()
    try:
        cursor = (
            collection.find(
                query,
                {"embedded_text": 1, "text": 1, "unit_title": 1},
            )
            .sort([("unit_index", 1), ("chunk_index", 1)])
            .limit(max(1, limit))
        )
        return list(cursor)
    finally:
        client.close()


def mark_chunks_embedded(updates: list[tuple[Any, list[float]]]) -> int:
    """Set embedding + embed_status=embedded for (chunk_id, vector) pairs."""
    if not updates:
        return 0
    if not settings.MONGODB_URL:
        raise RuntimeError("MONGODB_URL is not configured")

    from pymongo import UpdateOne

    client, collection = _sync_collection()
    try:
        ops = [
            UpdateOne(
                {"_id": chunk_id},
                {
                    "$set": {
                        "embedding": vector,
                        "embed_status": EMBED_STATUS_EMBEDDED,
                    },
                    "$unset": {"embed_error": ""},
                },
            )
            for chunk_id, vector in updates
        ]
        result = collection.bulk_write(ops, ordered=False)
        return int(result.modified_count)
    finally:
        client.close()


def mark_chunks_embed_failed(chunk_ids: list[Any], error: str) -> int:
    if not chunk_ids:
        return 0
    if not settings.MONGODB_URL:
        raise RuntimeError("MONGODB_URL is not configured")

    client, collection = _sync_collection()
    try:
        result = collection.update_many(
            {"_id": {"$in": chunk_ids}},
            {
                "$set": {
                    "embed_status": EMBED_STATUS_FAILED,
                    "embed_error": error[:500],
                    "embedding": None,
                }
            },
        )
        return int(result.modified_count)
    finally:
        client.close()


def count_pending_embed_chunks(book_id: int) -> int:
    if not settings.MONGODB_URL:
        return 0
    client, collection = _sync_collection()
    try:
        return int(
            collection.count_documents(
                {
                    "book_id": int(book_id),
                    "embed_status": {"$in": [EMBED_STATUS_PENDING, EMBED_STATUS_FAILED]},
                }
            )
        )
    finally:
        client.close()


async def ensure_book_chunks_indexes_async() -> None:
    """Create indexes via Motor when the app is already connected."""
    if not settings.MONGODB_URL:
        return
    try:
        db = get_mongo_db()
    except RuntimeError:
        return
    await db[BOOK_CHUNKS_COLLECTION].create_index(
        [("book_id", 1), ("unit_id", 1)],
        name="book_unit_idx",
    )
    await db[BOOK_CHUNKS_COLLECTION].create_index([("book_id", 1)], name="book_id_idx")
    await db[BOOK_CHUNKS_COLLECTION].create_index(
        [("book_id", 1), ("embed_status", 1)],
        name="book_embed_status_idx",
    )
