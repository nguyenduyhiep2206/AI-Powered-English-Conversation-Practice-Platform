"""Enrich book structure units with heuristic-first, weak-only LLM signals."""

from __future__ import annotations

import logging
import tempfile
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.book import BookDB
from app.models.book_structure_preview import BookStructurePreviewDB
from app.models.enums import BookStatusEnum
from app.services.book_chunk_service import get_unit_chunks
from app.services.book_indexing_service import extract_pages_text
from app.services.book_structure_service import _download_pdf_bytes
from app.services.skill_graph_service import load_catalog_skills
from app.services.unit_enrichment_excerpt import (
    join_chunk_texts,
    truncate_excerpt,
    window_prefer_language_focus,
)
from app.services.unit_enrichment_heuristic import HeuristicResult, run_heuristic
from app.services.unit_enrichment_llm import enrich_unit_signals_llm

logger = logging.getLogger(__name__)


@dataclass
class _UnitEnrichOutcome:
    status: str
    method: str
    source: str | None
    language_focus: str | None = None
    grammar_cues: list[str] | None = None
    vocab_cues: list[str] | None = None
    content_summary: str | None = None


def _empty_meta() -> dict[str, Any]:
    return {
        "enriched": 0,
        "method_counts": {"heuristic": 0, "heuristic+llm": 0, "skipped": 0},
        "source_counts": {"chunks": 0, "pdf_skim": 0},
    }


@contextmanager
def _temp_pdf(pdf_bytes: bytes) -> Iterator[str]:
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=True) as tmp:
        tmp.write(pdf_bytes)
        tmp.flush()
        yield tmp.name


async def _load_ready_book_and_units(
    db: AsyncSession, book_id: int
) -> tuple[BookDB, list[BookStructurePreviewDB]]:
    book = (await db.execute(select(BookDB).where(BookDB.id == book_id))).scalar_one_or_none()
    if book is None:
        raise ValueError(f"Không tìm thấy sách {book_id}")
    if book.status != BookStatusEnum.ready:
        raise ValueError("Sách phải ở trạng thái ready trước khi enrich units")
    units = list(
        (
            await db.execute(
                select(BookStructurePreviewDB)
                .where(BookStructurePreviewDB.book_id == book_id)
                .order_by(BookStructurePreviewDB.unit_index)
            )
        )
        .scalars()
        .all()
    )
    if not units:
        raise ValueError("Chưa có structure preview — chạy detect-structure trước")
    return book, units


class _PdfCache:
    """Download book PDF at most once for pdf_skim fallback."""

    def __init__(self, book: BookDB) -> None:
        self._book = book
        self._path: str | None = None
        self._cm: Any = None
        self._failed = False

    async def path(self) -> str | None:
        if self._failed:
            return None
        if self._path is not None:
            return self._path
        try:
            pdf_bytes = await _download_pdf_bytes(self._book)
            self._cm = _temp_pdf(pdf_bytes)
            self._path = self._cm.__enter__()
            return self._path
        except Exception:
            logger.exception("PDF download failed for book=%s", self._book.id)
            self._failed = True
            return None

    def close(self) -> None:
        if self._cm is not None:
            try:
                self._cm.__exit__(None, None, None)
            except Exception:
                logger.exception("temp pdf cleanup failed book=%s", self._book.id)
            self._cm = None
            self._path = None


async def _ensure_pdf_path(cache: _PdfCache) -> str | None:
    return await cache.path()


def _load_chunk_raw(book_id: int, unit_id: int) -> str:
    try:
        chunks = get_unit_chunks(book_id, unit_id)
    except Exception:
        logger.debug("get_unit_chunks failed book=%s unit=%s", book_id, unit_id, exc_info=True)
        return ""
    return join_chunk_texts(chunks or [])


async def _load_unit_raw(
    book_id: int,
    unit: BookStructurePreviewDB,
    pdf_cache: _PdfCache,
) -> tuple[str, str | None]:
    raw = _load_chunk_raw(book_id, int(unit.id))
    if raw.strip():
        return raw, "chunks"
    pdf_path = await _ensure_pdf_path(pdf_cache)
    if not pdf_path:
        return "", None
    try:
        text = extract_pages_text(pdf_path, int(unit.page_start), int(unit.page_end))
    except Exception:
        logger.exception(
            "pdf skim failed book=%s unit=%s", book_id, unit.id
        )
        return "", "pdf_skim"
    return text or "", "pdf_skim"


def _build_excerpt(raw: str) -> str:
    windowed = window_prefer_language_focus(raw)
    return truncate_excerpt(windowed, settings.UNIT_ENRICH_MAX_CHARS)


def _merge_unique(*lists: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for lst in lists:
        for item in lst:
            if item and item not in seen:
                seen.add(item)
                out.append(item)
    return out


def _merge_with_llm(heuristic: HeuristicResult, llm: dict[str, Any]) -> _UnitEnrichOutcome:
    focus = llm.get("language_focus") or heuristic.language_focus
    grammar = _merge_unique(list(heuristic.grammar_cues), list(llm.get("grammar_cues") or []))
    vocab = _merge_unique(list(heuristic.vocab_cues), list(llm.get("vocab_cues") or []))
    summary = llm.get("content_summary")
    return _UnitEnrichOutcome(
        status="done",
        method="heuristic+llm",
        source=None,
        language_focus=focus,
        grammar_cues=grammar,
        vocab_cues=vocab,
        content_summary=summary if isinstance(summary, str) else None,
    )


def _from_heuristic(heuristic: HeuristicResult, *, method: str = "heuristic") -> _UnitEnrichOutcome:
    return _UnitEnrichOutcome(
        status="done",
        method=method,
        source=None,
        language_focus=heuristic.language_focus,
        grammar_cues=list(heuristic.grammar_cues),
        vocab_cues=list(heuristic.vocab_cues),
        content_summary=None,
    )


def _heuristic_empty(heuristic: HeuristicResult) -> bool:
    return (
        not heuristic.language_focus
        and not heuristic.grammar_cues
        and not heuristic.vocab_cues
    )


def _should_call_llm(heuristic: HeuristicResult) -> bool:
    if heuristic.strong:
        return False
    if not settings.UNIT_ENRICH_LLM_ENABLED:
        return False
    if not settings.OPENAI_API_KEY:
        return False
    return True


def _enrich_signals(
    *,
    book: BookDB,
    unit: BookStructurePreviewDB,
    excerpt: str,
    catalog_skills: list[dict[str, Any]],
) -> _UnitEnrichOutcome:
    heuristic = run_heuristic(
        excerpt, unit_title=unit.title, catalog_skills=catalog_skills
    )
    if heuristic.strong:
        return _from_heuristic(heuristic)

    if not _should_call_llm(heuristic):
        return _from_heuristic(heuristic)

    cefr = book.cefr_level.value if hasattr(book.cefr_level, "value") else str(book.cefr_level)
    try:
        llm_payload = enrich_unit_signals_llm(
            cefr_level=cefr,
            book_title=book.title,
            unit_title=unit.title,
            excerpt=excerpt,
            catalog_skills=catalog_skills,
        )
        return _merge_with_llm(heuristic, llm_payload)
    except Exception:
        logger.exception("LLM enrich failed book=%s unit=%s", book.id, unit.id)
        if _heuristic_empty(heuristic):
            return _UnitEnrichOutcome(status="failed", method="heuristic", source=None)
        return _from_heuristic(heuristic)


def _apply_outcome(unit: BookStructurePreviewDB, outcome: _UnitEnrichOutcome) -> None:
    unit.language_focus = outcome.language_focus
    unit.grammar_cues = outcome.grammar_cues
    unit.vocab_cues = outcome.vocab_cues
    unit.content_summary = outcome.content_summary
    unit.enrichment_status = outcome.status
    unit.enrichment_method = outcome.method
    unit.enrichment_source = outcome.source
    unit.enriched_at = datetime.now(timezone.utc)


def _bump_meta(meta: dict[str, Any], outcome: _UnitEnrichOutcome) -> None:
    method = outcome.method
    if method in meta["method_counts"]:
        meta["method_counts"][method] += 1
    if outcome.source in meta["source_counts"]:
        meta["source_counts"][outcome.source] += 1
    if outcome.status == "done":
        meta["enriched"] += 1


async def _enrich_one_unit(
    book: BookDB,
    unit: BookStructurePreviewDB,
    catalog_skills: list[dict[str, Any]],
    pdf_cache: _PdfCache,
) -> _UnitEnrichOutcome:
    raw, source = await _load_unit_raw(int(book.id), unit, pdf_cache)
    excerpt = _build_excerpt(raw) if raw.strip() else ""
    if not excerpt.strip():
        return _UnitEnrichOutcome(
            status="skipped",
            method="skipped",
            source=source,
        )
    outcome = _enrich_signals(
        book=book, unit=unit, excerpt=excerpt, catalog_skills=catalog_skills
    )
    outcome.source = source
    return outcome


async def enrich_units_for_book(
    db: AsyncSession, book_id: int, *, force: bool = False
) -> dict[str, Any]:
    if not settings.UNIT_ENRICH_ENABLED:
        return _empty_meta()

    book, units = await _load_ready_book_and_units(db, book_id)
    catalog_skills = await load_catalog_skills(db, book.cefr_level) if book.cefr_level else []
    pdf_cache = _PdfCache(book)
    meta = _empty_meta()
    try:
        for unit in units:
            if not force and unit.enrichment_status == "done":
                continue
            outcome = await _enrich_one_unit(book, unit, catalog_skills, pdf_cache)
            _apply_outcome(unit, outcome)
            _bump_meta(meta, outcome)
        await db.commit()
    finally:
        pdf_cache.close()
    return meta
