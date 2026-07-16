import logging
import tempfile
from dataclasses import dataclass

import httpx
from fastapi import HTTPException, status
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import AsyncSessionLocal
from app.models.book import BookDB
from app.models.book_structure_preview import BookStructurePreviewDB
from app.models.enums import BookStatusEnum
from app.services.book_structure.detector_chain import StructureDetectorChain
from app.services import supabase_storage_service
from app.services.book_service import get_book

logger = logging.getLogger(__name__)


@dataclass
class StructurePreviewSummary:
    book_id: int
    detection_method: str | None
    confidence: float | None
    status: BookStatusEnum
    units: list[BookStructurePreviewDB]


def status_after_successful_detect(confidence: float) -> BookStatusEnum:
    """After units are saved, always require human review before chunking."""
    _ = confidence
    return BookStatusEnum.needs_review


async def _download_pdf_bytes(book: BookDB) -> bytes:
    if book.file_public_id and supabase_storage_service.is_configured():
        try:
            return supabase_storage_service.download_pdf(book.file_public_id)
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Failed to download PDF from Supabase Storage: {exc}",
            ) from exc

    if not book.file_path:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Book has no file URL")

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.get(book.file_path)
            response.raise_for_status()
            return response.content
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to download PDF: {exc}",
        ) from exc


async def get_structure_preview(db: AsyncSession, book_id: int) -> StructurePreviewSummary:
    book = await get_book(db, book_id)
    result = await db.execute(
        select(BookStructurePreviewDB)
        .where(BookStructurePreviewDB.book_id == book_id)
        .order_by(BookStructurePreviewDB.unit_index)
    )
    units = list(result.scalars().all())
    confidence = units[0].confidence if units else None
    return StructurePreviewSummary(
        book_id=int(book.id),
        detection_method=book.detection_method,
        confidence=confidence,
        status=book.status,
        units=units,
    )


async def detect_book_structure(db: AsyncSession, book_id: int) -> StructurePreviewSummary:
    book = await get_book(db, book_id)
    if not book.file_path:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Book has no file URL")

    pdf_bytes = await _download_pdf_bytes(book)

    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=True) as tmp:
        tmp.write(pdf_bytes)
        tmp.flush()
        detection = StructureDetectorChain().detect(tmp.name)

    if detection is None or not detection.units:
        book.detection_method = None
        book.status = BookStatusEnum.needs_review
        await db.execute(delete(BookStructurePreviewDB).where(BookStructurePreviewDB.book_id == book_id))
        await db.commit()
        await db.refresh(book)
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Could not detect book structure from this PDF",
        )

    await db.execute(delete(BookStructurePreviewDB).where(BookStructurePreviewDB.book_id == book_id))

    preview_rows = [
        BookStructurePreviewDB(
            book_id=book_id,
            unit_index=index,
            title=unit.title,
            page_start=unit.page_start,
            page_end=unit.page_end,
            detection_method=detection.method,
            confidence=detection.confidence,
            depth_or_source=unit.depth_or_source,
        )
        for index, unit in enumerate(detection.units)
    ]
    db.add_all(preview_rows)

    book.detection_method = detection.method
    book.status = status_after_successful_detect(detection.confidence)

    await db.commit()
    await db.refresh(book)

    refreshed = await db.execute(
        select(BookStructurePreviewDB)
        .where(BookStructurePreviewDB.book_id == book_id)
        .order_by(BookStructurePreviewDB.unit_index)
    )
    saved_units = list(refreshed.scalars().all())

    return StructurePreviewSummary(
        book_id=int(book.id),
        detection_method=book.detection_method,
        confidence=detection.confidence,
        status=book.status,
        units=saved_units,
    )


async def detect_book_structure_job(book_id: int) -> None:
    """Background entry: open own DB session (same pattern as index_book)."""
    try:
        async with AsyncSessionLocal() as db:
            await detect_book_structure(db, book_id)
    except HTTPException as exc:
        logger.warning("Structure detect rejected for book_id=%s: %s", book_id, exc.detail)
    except Exception:
        logger.exception("Background structure detect failed for book_id=%s", book_id)
        try:
            async with AsyncSessionLocal() as db:
                book = await get_book(db, book_id)
                if book.status == BookStatusEnum.uploaded:
                    book.status = BookStatusEnum.needs_review
                    await db.commit()
        except Exception:
            logger.exception("Failed to mark book_id=%s after detect error", book_id)
