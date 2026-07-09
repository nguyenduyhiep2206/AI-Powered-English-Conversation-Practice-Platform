"""Delete indexed chunks from MongoDB when configured (Phase 2 indexing)."""

from app.core.config import settings

BOOK_CHUNKS_COLLECTION = "book_chunks"


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
