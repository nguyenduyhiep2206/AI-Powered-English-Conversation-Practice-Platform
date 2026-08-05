"""Orchestrator tests: heuristic-first, weak-only LLM (mocked I/O)."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

from app.core.config import settings
from app.models.enums import BookStatusEnum, CEFRLevel
from app.services import unit_enrichment_service as ues
from app.services.unit_enrichment_heuristic import HeuristicResult

CATALOG = [
    {"slug": "present_simple", "title": "Present simple", "difficulty_in_level": 5},
    {"slug": "modals_should_must", "title": "Should / must", "difficulty_in_level": 6},
]


def _ready_book(**kwargs):
    book = MagicMock()
    book.id = 1
    book.title = "Empower Elementary"
    book.status = BookStatusEnum.ready
    book.cefr_level = CEFRLevel.A2
    for k, v in kwargs.items():
        setattr(book, k, v)
    return book


def _unit(**kwargs):
    u = MagicMock()
    u.id = kwargs.get("id", 10)
    u.unit_index = kwargs.get("unit_index", 0)
    u.title = kwargs.get("title", "Unit 1 People")
    u.page_start = kwargs.get("page_start", 1)
    u.page_end = kwargs.get("page_end", 5)
    u.enrichment_status = kwargs.get("enrichment_status")
    u.language_focus = None
    u.grammar_cues = None
    u.vocab_cues = None
    u.content_summary = None
    u.enriched_at = None
    u.enrichment_source = None
    u.enrichment_method = None
    return u


def test_strong_heuristic_skips_llm():
    book = _ready_book()
    unit = _unit()
    db = AsyncMock()
    db.commit = AsyncMock()
    strong = HeuristicResult(
        language_focus="present simple for routines",
        grammar_cues=["present_simple"],
        vocab_cues=["people"],
        strong=True,
    )
    llm = MagicMock()

    async def run():
        with (
            patch.object(
                ues, "_load_ready_book_and_units", AsyncMock(return_value=(book, [unit]))
            ),
            patch.object(ues, "load_catalog_skills", AsyncMock(return_value=CATALOG)),
            patch.object(
                ues,
                "get_unit_chunks",
                return_value=[
                    {"chunk_index": 0, "text": "Grammar\nWe use the present simple."}
                ],
            ),
            patch.object(ues, "run_heuristic", return_value=strong),
            patch.object(ues, "enrich_unit_signals_llm", llm),
            patch.object(ues.settings, "UNIT_ENRICH_ENABLED", True),
            patch.object(ues.settings, "UNIT_ENRICH_LLM_ENABLED", True),
            patch.object(ues.settings, "OPENAI_API_KEY", "sk-test"),
        ):
            return await ues.enrich_units_for_book(db, 1)

    meta = asyncio.run(run())

    llm.assert_not_called()
    assert unit.enrichment_status == "done"
    assert unit.enrichment_method == "heuristic"
    assert unit.enrichment_source == "chunks"
    assert unit.grammar_cues == ["present_simple"]
    assert meta["enriched"] == 1
    assert meta["method_counts"]["heuristic"] == 1
    assert meta["source_counts"]["chunks"] == 1


def test_weak_heuristic_calls_llm_once():
    book = _ready_book()
    unit = _unit(title="Unit 1 People")
    db = AsyncMock()
    db.commit = AsyncMock()
    weak = HeuristicResult(
        language_focus=None,
        grammar_cues=[],
        vocab_cues=["people"],
        strong=False,
    )
    long_body = "Thematic reading about people. " * 200  # > MAX_CHARS when joined
    llm = MagicMock(
        return_value={
            "language_focus": "present simple",
            "grammar_cues": ["present_simple"],
            "vocab_cues": ["people", "jobs"],
            "content_summary": "Unit introduces people and daily routines.",
        }
    )

    async def run():
        with (
            patch.object(
                ues, "_load_ready_book_and_units", AsyncMock(return_value=(book, [unit]))
            ),
            patch.object(ues, "load_catalog_skills", AsyncMock(return_value=CATALOG)),
            patch.object(
                ues,
                "get_unit_chunks",
                return_value=[{"chunk_index": 0, "text": long_body}],
            ),
            patch.object(ues, "run_heuristic", return_value=weak),
            patch.object(ues, "enrich_unit_signals_llm", llm),
            patch.object(ues.settings, "UNIT_ENRICH_ENABLED", True),
            patch.object(ues.settings, "UNIT_ENRICH_LLM_ENABLED", True),
            patch.object(ues.settings, "UNIT_ENRICH_MAX_CHARS", settings.UNIT_ENRICH_MAX_CHARS),
            patch.object(ues.settings, "OPENAI_API_KEY", "sk-test"),
        ):
            return await ues.enrich_units_for_book(db, 1)

    meta = asyncio.run(run())

    llm.assert_called_once()
    call_kwargs = llm.call_args.kwargs
    assert len(call_kwargs["excerpt"]) <= settings.UNIT_ENRICH_MAX_CHARS
    assert unit.enrichment_status == "done"
    assert unit.enrichment_method == "heuristic+llm"
    assert unit.enrichment_source == "chunks"
    assert "present_simple" in unit.grammar_cues
    assert unit.content_summary is not None
    assert meta["method_counts"]["heuristic+llm"] == 1
    assert meta["enriched"] == 1


def test_empty_excerpt_skipped_no_llm():
    book = _ready_book()
    unit = _unit()
    db = AsyncMock()
    db.commit = AsyncMock()
    llm = MagicMock()
    heuristic = MagicMock()

    async def run():
        with (
            patch.object(
                ues, "_load_ready_book_and_units", AsyncMock(return_value=(book, [unit]))
            ),
            patch.object(ues, "load_catalog_skills", AsyncMock(return_value=CATALOG)),
            patch.object(ues, "get_unit_chunks", return_value=[]),
            patch.object(ues, "_ensure_pdf_path", AsyncMock(return_value=None)),
            patch.object(ues, "run_heuristic", heuristic),
            patch.object(ues, "enrich_unit_signals_llm", llm),
            patch.object(ues.settings, "UNIT_ENRICH_ENABLED", True),
            patch.object(ues.settings, "UNIT_ENRICH_LLM_ENABLED", True),
            patch.object(ues.settings, "OPENAI_API_KEY", "sk-test"),
        ):
            return await ues.enrich_units_for_book(db, 1)

    meta = asyncio.run(run())

    llm.assert_not_called()
    heuristic.assert_not_called()
    assert unit.enrichment_status == "skipped"
    assert unit.enrichment_method == "skipped"
    assert meta["method_counts"]["skipped"] == 1
    assert meta["enriched"] == 0


def test_force_false_skips_done_units():
    book = _ready_book()
    unit = _unit(enrichment_status="done")
    db = AsyncMock()
    db.commit = AsyncMock()
    load_raw = AsyncMock()

    async def run():
        with (
            patch.object(
                ues, "_load_ready_book_and_units", AsyncMock(return_value=(book, [unit]))
            ),
            patch.object(ues, "load_catalog_skills", AsyncMock(return_value=CATALOG)),
            patch.object(ues, "_enrich_one_unit", load_raw),
            patch.object(ues.settings, "UNIT_ENRICH_ENABLED", True),
        ):
            return await ues.enrich_units_for_book(db, 1, force=False)

    meta = asyncio.run(run())
    load_raw.assert_not_called()
    assert meta["enriched"] == 0
    db.commit.assert_awaited()


def test_force_true_reenriches_done_units():
    book = _ready_book()
    unit = _unit(enrichment_status="done")
    db = AsyncMock()
    db.commit = AsyncMock()
    strong = HeuristicResult(
        language_focus="modals",
        grammar_cues=["modals_should_must"],
        vocab_cues=[],
        strong=True,
    )
    llm = MagicMock()

    async def run():
        with (
            patch.object(
                ues, "_load_ready_book_and_units", AsyncMock(return_value=(book, [unit]))
            ),
            patch.object(ues, "load_catalog_skills", AsyncMock(return_value=CATALOG)),
            patch.object(
                ues,
                "get_unit_chunks",
                return_value=[{"chunk_index": 0, "text": "Language focus\nshould / must"}],
            ),
            patch.object(ues, "run_heuristic", return_value=strong),
            patch.object(ues, "enrich_unit_signals_llm", llm),
            patch.object(ues.settings, "UNIT_ENRICH_ENABLED", True),
            patch.object(ues.settings, "UNIT_ENRICH_LLM_ENABLED", True),
            patch.object(ues.settings, "OPENAI_API_KEY", "sk-test"),
        ):
            return await ues.enrich_units_for_book(db, 1, force=True)

    meta = asyncio.run(run())
    llm.assert_not_called()
    assert unit.enrichment_status == "done"
    assert unit.enrichment_method == "heuristic"
    assert meta["enriched"] == 1
