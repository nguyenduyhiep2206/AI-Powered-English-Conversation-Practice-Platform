import logging
import tempfile
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass

import httpx
from fastapi import HTTPException, status
from pypdf import PdfReader
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.models.book import BookDB
from app.models.book_structure_preview import BookStructurePreviewDB
from app.models.enums import BookStatusEnum
from app.services.book_structure.ai_merge_service import merge_structure_with_ai, skim_pdf_headings
from app.services.book_structure.base import DetectionResult
from app.services.book_structure.detector_chain import StructureDetectorChain
from app.services.book_structure.structure_gate import validate_structure
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


@dataclass
class StructureDetectOutcome:
    summary: StructurePreviewSummary
    should_index: bool


def status_after_successful_detect(confidence: float) -> BookStatusEnum:
    """Legacy helper — prefer status_after_structure_decision for new flow."""
    _ = confidence
    return BookStatusEnum.needs_review


def status_after_structure_decision(*, gate_ok: bool, auto_index_enabled: bool) -> BookStatusEnum:
    if auto_index_enabled and gate_ok:
        return BookStatusEnum.processing
    return BookStatusEnum.needs_review


def pick_best_candidate(candidates: list[DetectionResult]) -> DetectionResult | None:
    if not candidates:
        return None
    return max(candidates, key=lambda r: (len(r.units), r.confidence))


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


async def _load_preview_units(db: AsyncSession, book_id: int) -> list[BookStructurePreviewDB]:
    result = await db.execute(
        select(BookStructurePreviewDB)
        .where(BookStructurePreviewDB.book_id == book_id)
        .order_by(BookStructurePreviewDB.unit_index)
    )
    return list(result.scalars().all())


def _build_summary(
    book: BookDB, confidence: float | None, units: list[BookStructurePreviewDB]
) -> StructurePreviewSummary:
    return StructurePreviewSummary(
        book_id=int(book.id),
        detection_method=book.detection_method,
        confidence=confidence,
        status=book.status,
        units=units,
    )


async def get_structure_preview(db: AsyncSession, book_id: int) -> StructurePreviewSummary:
    book = await get_book(db, book_id)
    units = await _load_preview_units(db, book_id)
    confidence = units[0].confidence if units else None
    return _build_summary(book, confidence, units)


@contextmanager
def _temp_pdf(pdf_bytes: bytes) -> Iterator[str]:
    """Yield a temp file path holding the PDF bytes; auto-cleaned on exit."""
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=True) as tmp:
        tmp.write(pdf_bytes)
        tmp.flush()
        yield tmp.name


def _resolve_detection(pdf_path: str) -> tuple[DetectionResult | None, bool, list[str], int]:
    """Return (detection, auto_index_enabled, page_texts_for_gate, total_pages)."""
    chain = StructureDetectorChain()
    candidates = chain.detect_all(pdf_path)
    total_pages = len(PdfReader(pdf_path).pages)
    page_texts = skim_pdf_headings(pdf_path)

    use_ai = bool(settings.STRUCTURE_AI_MERGE_ENABLED and settings.OPENAI_API_KEY)
    detection: DetectionResult | None = None

    if use_ai:
        if candidates:
            try:
                detection = merge_structure_with_ai(
                    pdf_path, candidates, total_pages=total_pages
                )
            except Exception:
                logger.exception("AI structure merge failed; falling back to best candidate")
                detection = pick_best_candidate(candidates)
        else:
            try:
                detection = merge_structure_with_ai(pdf_path, [], total_pages=total_pages)
            except Exception:
                logger.exception("AI structure merge failed with no heuristic candidates")
                detection = None
    else:
        detection = pick_best_candidate(candidates) or chain.detect(pdf_path)

    return detection, use_ai, page_texts, total_pages


def _detect_from_pdf(pdf_bytes: bytes) -> tuple[DetectionResult | None, bool, list[str], int]:
    with _temp_pdf(pdf_bytes) as pdf_path:
        return _resolve_detection(pdf_path)


async def _clear_preview(db: AsyncSession, book_id: int) -> None:
    await db.execute(delete(BookStructurePreviewDB).where(BookStructurePreviewDB.book_id == book_id))


async def _reset_to_needs_review(db: AsyncSession, book: BookDB, book_id: int) -> None:
    book.detection_method = None
    book.status = BookStatusEnum.needs_review
    await _clear_preview(db, book_id)
    await db.commit()
    await db.refresh(book)


def _run_structure_gate(
    book_id: int, detection: DetectionResult, page_texts: list[str], total_pages: int
) -> bool:
    while len(page_texts) < total_pages:  # pad so gate sees every page
        page_texts.append("")
    gate_ok, gate_reasons = validate_structure(
        detection.units, total_pages=total_pages, page_texts=page_texts
    )
    if not gate_ok:
        logger.warning(
            "Structure gate failed for book_id=%s method=%s: %s",
            book_id,
            detection.method,
            "; ".join(gate_reasons),
        )
    return gate_ok


async def _save_preview_rows(db: AsyncSession, book_id: int, detection: DetectionResult) -> None:
    await _clear_preview(db, book_id)
    db.add_all(
        [
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
    )


async def detect_book_structure(db: AsyncSession, book_id: int) -> StructureDetectOutcome:
    book = await get_book(db, book_id)
    if not book.file_path:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Book has no file URL")

    pdf_bytes = await _download_pdf_bytes(book)
    detection, auto_index_enabled, page_texts, total_pages = _detect_from_pdf(pdf_bytes)

    if detection is None or not detection.units:
        await _reset_to_needs_review(db, book, book_id)
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Could not detect book structure from this PDF",
        )

    gate_ok = _run_structure_gate(book_id, detection, page_texts, total_pages)
    await _save_preview_rows(db, book_id, detection)

    book.detection_method = detection.method
    book.status = status_after_structure_decision(
        gate_ok=gate_ok, auto_index_enabled=auto_index_enabled
    )
    should_index = book.status == BookStatusEnum.processing
    await db.commit()
    await db.refresh(book)

    units = await _load_preview_units(db, book_id)
    summary = _build_summary(book, detection.confidence, units)
    return StructureDetectOutcome(summary=summary, should_index=should_index)


async def detect_book_structure_job(book_id: int) -> None:
    """Background entry: detect (+ optional AI merge/gate); auto-index when gate passes."""
    should_index = False
    try:
        async with AsyncSessionLocal() as db:
            outcome = await detect_book_structure(db, book_id)
            should_index = outcome.should_index
    except HTTPException as exc:
        logger.warning("Structure detect rejected for book_id=%s: %s", book_id, exc.detail)
        return
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
        return

    if should_index:
        from app.services.book_indexing_service import index_book

        try:
            await index_book(book_id)
        except Exception:
            logger.exception("Auto-index failed for book_id=%s after structure gate pass", book_id)
