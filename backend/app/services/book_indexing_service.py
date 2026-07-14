"""Chunk book units and persist to MongoDB, then embed via Voyage in a second phase.

Phase 1 (local): extract → chunk → save text with embed_status=pending.
Phase 2 (Voyage): embed pending/failed chunks in small batches with delay/retry.
Overlap stays inside a single unit — never across unit boundaries.
"""

from __future__ import annotations

import logging
import tempfile
import time
from typing import Any

import pdfplumber
from langchain_text_splitters import RecursiveCharacterTextSplitter
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.models.book import BookDB
from app.models.book_structure_preview import BookStructurePreviewDB
from app.models.enums import BookStatusEnum, BookTypeEnum
from app.services.book_chunk_service import (
    EMBED_STATUS_PENDING,
    count_book_chunks,
    count_pending_embed_chunks,
    delete_book_chunks,
    delete_unit_chunks,
    ensure_book_chunks_indexes,
    fetch_pending_embed_chunks,
    insert_chunks,
    mark_chunks_embed_failed,
    mark_chunks_embedded,
)
from app.services.book_structure_service import _download_pdf_bytes
from app.services.embedding_service import embed_texts

logger = logging.getLogger(__name__)

CHUNK_SETTINGS: dict[BookTypeEnum, tuple[int, int]] = {
    BookTypeEnum.grammar_textbook: (1200, 100),
    BookTypeEnum.reading_practice: (800, 80),
    BookTypeEnum.test_bank: (800, 80),
    BookTypeEnum.freeform: (600, 100),
}

SEPARATORS = ["\n\n", "\n", ". ", " "]


def build_embedded_text(unit_title: str, chunk_text: str) -> str:
    return f"[{unit_title}]\n{chunk_text}"


def chunk_unit_text(text: str, book_type: BookTypeEnum) -> list[str]:
    cleaned = text.strip()
    if not cleaned:
        return []

    chunk_size, overlap = CHUNK_SETTINGS.get(book_type, CHUNK_SETTINGS[BookTypeEnum.freeform])
    # Short sections stay whole — splitter returns a single chunk when len <= chunk_size.
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=overlap,
        separators=SEPARATORS,
        length_function=len,
    )
    return splitter.split_text(cleaned)


def extract_pages_text(pdf_path: str, page_start: int, page_end: int) -> str:
    """Extract text for inclusive 1-based page range."""
    parts: list[str] = []
    with pdfplumber.open(pdf_path) as pdf:
        total = len(pdf.pages)
        start = max(1, page_start)
        end = min(total, page_end)
        for page_number in range(start, end + 1):
            page = pdf.pages[page_number - 1]
            parts.append(page.extract_text() or "")
    return "\n".join(parts).strip()


def index_unit_chunks(book: Any, unit: Any, pdf_path: str) -> list[dict[str, Any]]:
    """Build MongoDB docs for one unit (text only). Embeddings filled in phase 2.

    Raises ValueError if text/chunks are empty. Does not call Voyage.
    """
    text = extract_pages_text(pdf_path, int(unit.page_start), int(unit.page_end))
    if not text:
        raise ValueError(f"empty text for unit_id={unit.id} title={unit.title!r}")

    book_type = book.book_type if isinstance(book.book_type, BookTypeEnum) else BookTypeEnum(book.book_type)
    chunks = chunk_unit_text(text, book_type)
    if not chunks:
        raise ValueError(f"empty chunks for unit_id={unit.id} title={unit.title!r}")

    cefr = None
    if book.cefr_level is not None:
        cefr = book.cefr_level.value if hasattr(book.cefr_level, "value") else str(book.cefr_level)

    docs: list[dict[str, Any]] = []
    for index, chunk in enumerate(chunks):
        embedded = build_embedded_text(unit.title, chunk)
        docs.append(
            {
                "book_id": int(book.id),
                "unit_id": int(unit.id),
                "unit_title": unit.title,
                "unit_index": int(unit.unit_index),
                "chunk_index": index,
                "page_start": int(unit.page_start),
                "page_end": int(unit.page_end),
                "text": chunk,
                "embedded_text": embedded,
                "embedding": None,
                "embed_status": EMBED_STATUS_PENDING,
                "detection_method": book.detection_method,
                "metadata": {
                    "book_type": book_type.value,
                    "cefr_level": cefr,
                },
            }
        )
    return docs


def embed_pending_chunks(book_id: int, *, unit_id: int | None = None) -> dict[str, int]:
    """Phase 2: embed pending/failed chunks for a book (best-effort).

    Rate-limit friendly: small batches + delay between batches. Failures mark
    chunks as embed_status=failed but never delete saved text.
    """
    batch_size = max(1, int(settings.VOYAGE_EMBED_BATCH_SIZE or 32))
    delay = max(0.0, float(settings.VOYAGE_EMBED_BATCH_DELAY_SECONDS or 0.0))

    embedded = 0
    failed = 0

    while True:
        pending = fetch_pending_embed_chunks(book_id, unit_id=unit_id, limit=batch_size)
        if not pending:
            break

        texts: list[str] = []
        ids: list[Any] = []
        for doc in pending:
            text = (doc.get("embedded_text") or "").strip()
            if not text:
                title = doc.get("unit_title") or ""
                body = (doc.get("text") or "").strip()
                text = build_embedded_text(title, body) if body else ""
            if not text:
                mark_chunks_embed_failed([doc["_id"]], "empty embedded_text")
                failed += 1
                continue
            texts.append(text)
            ids.append(doc["_id"])

        if not texts:
            continue

        try:
            vectors = embed_texts(texts)
            if len(vectors) != len(ids):
                raise RuntimeError(
                    f"embedding count mismatch: got {len(vectors)} for {len(ids)} chunks"
                )
            mark_chunks_embedded(list(zip(ids, vectors)))
            embedded += len(ids)
            logger.info(
                "Embedded book=%s unit=%s batch=%s",
                book_id,
                unit_id,
                len(ids),
            )
        except Exception as exc:
            mark_chunks_embed_failed(ids, str(exc))
            failed += len(ids)
            logger.exception(
                "Embed batch failed book=%s unit=%s size=%s",
                book_id,
                unit_id,
                len(ids),
            )
            # Stop loop on hard failure for this pass; retry-embed can resume later.
            break

        if delay > 0:
            time.sleep(delay)

    pending_left = count_pending_embed_chunks(book_id)
    return {"embedded": embedded, "failed": failed, "pending_left": pending_left}


async def _load_book_and_units(
    db: AsyncSession, book_id: int, unit_id: int | None = None
) -> tuple[BookDB, list[BookStructurePreviewDB]]:
    result = await db.execute(select(BookDB).where(BookDB.id == book_id))
    book = result.scalar_one_or_none()
    if book is None:
        raise ValueError(f"Book {book_id} not found")

    query = (
        select(BookStructurePreviewDB)
        .where(BookStructurePreviewDB.book_id == book_id)
        .order_by(BookStructurePreviewDB.unit_index)
    )
    if unit_id is not None:
        query = query.where(BookStructurePreviewDB.id == unit_id)

    units_result = await db.execute(query)
    units = list(units_result.scalars().all())
    return book, units


async def index_book(book_id: int) -> None:
    """Phase 1 chunk all units, mark ready, then best-effort Voyage embed (phase 2)."""
    ensure_book_chunks_indexes()

    async with AsyncSessionLocal() as db:
        book, units = await _load_book_and_units(db, book_id)
        if not units:
            book.status = BookStatusEnum.failed
            await db.commit()
            logger.error("Book %s has no structure preview units to index", book_id)
            return

        pdf_bytes = await _download_pdf_bytes(book)
        failed_units: list[str] = []
        all_docs: list[dict[str, Any]] = []

        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=True) as tmp:
            tmp.write(pdf_bytes)
            tmp.flush()

            for unit in units:
                try:
                    docs = index_unit_chunks(book, unit, tmp.name)
                    all_docs.extend(docs)
                except Exception as exc:
                    failed_units.append(f"unit_id={unit.id} title={unit.title!r}: {exc}")
                    logger.exception("Failed chunking book=%s unit=%s", book_id, unit.id)

        delete_book_chunks(book_id)
        if all_docs:
            insert_chunks(all_docs)

        book.chunk_count = len(all_docs)
        if not all_docs:
            book.status = BookStatusEnum.failed
            await db.commit()
            logger.error(
                "Book %s chunking produced no docs — %s unit(s) failed: %s",
                book_id,
                len(failed_units),
                "; ".join(failed_units),
            )
            return

        # Text chunks are enough for unit-scoped quiz generation.
        book.status = BookStatusEnum.ready
        await db.commit()
        if failed_units:
            logger.warning(
                "Book %s ready with partial chunking — %s unit(s) failed: %s",
                book_id,
                len(failed_units),
                "; ".join(failed_units),
            )
        else:
            logger.info("Book %s chunked successfully chunks=%s", book_id, len(all_docs))

    # Phase 2 outside the DB transaction — does not roll back ready status.
    try:
        stats = embed_pending_chunks(book_id)
        logger.info("Book %s embed phase done %s", book_id, stats)
    except Exception:
        logger.exception("Book %s embed phase crashed; text chunks retained", book_id)


async def reindex_unit(book_id: int, unit_id: int) -> None:
    """Re-chunk a single unit (phase 1), then embed that unit (phase 2)."""
    ensure_book_chunks_indexes()

    async with AsyncSessionLocal() as db:
        book, units = await _load_book_and_units(db, book_id, unit_id=unit_id)
        if not units:
            raise ValueError(f"Unit {unit_id} not found for book {book_id}")

        unit = units[0]
        book.status = BookStatusEnum.processing
        await db.commit()

        pdf_bytes = await _download_pdf_bytes(book)

        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=True) as tmp:
            tmp.write(pdf_bytes)
            tmp.flush()
            try:
                docs = index_unit_chunks(book, unit, tmp.name)
            except Exception as exc:
                book.status = BookStatusEnum.failed
                await db.commit()
                logger.exception("Reindex chunking failed book=%s unit=%s", book_id, unit_id)
                raise ValueError(str(exc)) from exc

        delete_unit_chunks(book_id, unit_id)
        insert_chunks(docs)
        book.chunk_count = count_book_chunks(book_id)
        book.status = BookStatusEnum.ready
        await db.commit()
        logger.info("Rechunked book=%s unit=%s chunks=%s", book_id, unit_id, len(docs))

    try:
        stats = embed_pending_chunks(book_id, unit_id=unit_id)
        logger.info("Reindex embed book=%s unit=%s %s", book_id, unit_id, stats)
    except Exception:
        logger.exception(
            "Reindex embed failed book=%s unit=%s; text chunks retained",
            book_id,
            unit_id,
        )


async def retry_embeddings(book_id: int) -> dict[str, int]:
    """Resume Voyage embeddings for pending/failed chunks without re-chunking."""
    ensure_book_chunks_indexes()
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(BookDB).where(BookDB.id == book_id))
        book = result.scalar_one_or_none()
        if book is None:
            raise ValueError(f"Book {book_id} not found")

    return embed_pending_chunks(book_id)


async def confirm_and_start_indexing(db: AsyncSession, book_id: int) -> BookDB:
    """Validate preview exists, set status=processing. Caller schedules background job."""
    result = await db.execute(select(BookDB).where(BookDB.id == book_id))
    book = result.scalar_one_or_none()
    if book is None:
        from fastapi import HTTPException, status

        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Book not found")

    units_result = await db.execute(
        select(BookStructurePreviewDB).where(BookStructurePreviewDB.book_id == book_id)
    )
    units = list(units_result.scalars().all())
    if not units:
        from fastapi import HTTPException, status

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No structure preview to confirm. Run detect-structure first.",
        )

    book.status = BookStatusEnum.processing
    await db.commit()
    await db.refresh(book)
    return book
