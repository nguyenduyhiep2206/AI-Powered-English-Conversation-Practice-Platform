"""Unit tests for book indexing (chunking + pipeline) with mocked embeddings."""

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

from app.models.enums import BookTypeEnum
from app.services.book_indexing_service import (
    CHUNK_SETTINGS,
    build_embedded_text,
    chunk_unit_text,
    extract_pages_text,
    index_unit_chunks,
)


def _make_multi_page_pdf(path: Path, pages: list[str]) -> Path:
    c = canvas.Canvas(str(path), pagesize=letter)
    for text in pages:
        c.setFont("Helvetica", 12)
        c.drawString(72, 720, text)
        c.showPage()
    c.save()
    return path


def test_chunk_settings_by_book_type():
    assert CHUNK_SETTINGS[BookTypeEnum.grammar_textbook] == (1200, 100)
    assert CHUNK_SETTINGS[BookTypeEnum.reading_practice] == (800, 80)
    assert CHUNK_SETTINGS[BookTypeEnum.test_bank] == (800, 80)
    assert CHUNK_SETTINGS[BookTypeEnum.freeform] == (600, 100)


def test_short_grammar_section_not_split():
    text = "Present perfect is used for past actions with present relevance. " * 5
    assert len(text) < 1200
    chunks = chunk_unit_text(text, BookTypeEnum.grammar_textbook)
    assert len(chunks) == 1
    assert chunks[0] == text.strip()


def test_long_text_is_split_within_unit():
    text = ("Sentence about grammar. " * 80) + "\n\n" + ("Another paragraph here. " * 80)
    chunks = chunk_unit_text(text, BookTypeEnum.freeform)
    assert len(chunks) >= 2
    assert all(len(chunk) <= 600 + 50 for chunk in chunks)  # allow small overshoot from splitter


def test_build_embedded_text_adds_unit_header_only_for_embedding():
    original = "Body of the passage."
    embedded = build_embedded_text("PASSAGE 1: Silk", original)
    assert embedded == "[PASSAGE 1: Silk]\nBody of the passage."
    assert original == "Body of the passage."


def test_extract_pages_text_only_requested_range(tmp_path: Path):
    pdf = _make_multi_page_pdf(
        tmp_path / "pages.pdf",
        ["Page one content", "Page two content", "Page three content"],
    )
    text = extract_pages_text(str(pdf), page_start=2, page_end=3)
    assert "Page two content" in text
    assert "Page three content" in text
    assert "Page one content" not in text


def test_index_unit_chunks_does_not_cross_unit_boundaries(tmp_path: Path):
    """Each unit is chunked independently; Voyage is not called in phase 1."""
    pdf = _make_multi_page_pdf(
        tmp_path / "book.pdf",
        [
            "Unit A only text " * 40,
            "Unit B only text " * 40,
        ],
    )

    unit_a = SimpleNamespace(
        id=101,
        unit_index=0,
        title="Unit A",
        page_start=1,
        page_end=1,
    )
    unit_b = SimpleNamespace(
        id=102,
        unit_index=1,
        title="Unit B",
        page_start=2,
        page_end=2,
    )
    book = SimpleNamespace(
        id=7,
        book_type=BookTypeEnum.reading_practice,
        cefr_level=None,
        detection_method="regex",
    )

    with patch("app.services.book_indexing_service.embed_texts") as embed_mock:
        docs_a = index_unit_chunks(book, unit_a, str(pdf))
        docs_b = index_unit_chunks(book, unit_b, str(pdf))

    assert docs_a
    assert docs_b
    assert all(doc["unit_id"] == 101 for doc in docs_a)
    assert all(doc["unit_id"] == 102 for doc in docs_b)
    assert all(doc["text"].startswith("[") is False for doc in docs_a)
    assert all(doc["embedded_text"].startswith("[Unit A]\n") for doc in docs_a)
    assert all(doc["embedded_text"].startswith("[Unit B]\n") for doc in docs_b)
    assert all(doc["embedding"] is None for doc in docs_a + docs_b)
    assert all(doc["embed_status"] == "pending" for doc in docs_a + docs_b)
    assert all("Unit B only" not in doc["text"] for doc in docs_a)
    assert all("Unit A only" not in doc["text"] for doc in docs_b)
    assert not embed_mock.called
    assert len({(d["unit_id"], d["chunk_index"]) for d in docs_a + docs_b}) == len(docs_a) + len(docs_b)


def test_embed_pending_chunks_marks_embedded(monkeypatch):
    from app.services import book_indexing_service

    pending = [
        {"_id": "id1", "embedded_text": "[U]\none", "text": "one", "unit_title": "U"},
        {"_id": "id2", "embedded_text": "[U]\ntwo", "text": "two", "unit_title": "U"},
    ]
    state = {"once": True}

    def fetch_once(book_id, unit_id=None, limit=32):
        if state["once"]:
            state["once"] = False
            return pending
        return []

    monkeypatch.setattr(book_indexing_service, "fetch_pending_embed_chunks", fetch_once)
    monkeypatch.setattr(
        book_indexing_service,
        "embed_texts",
        lambda texts: [[0.1, 0.2] for _ in texts],
    )
    monkeypatch.setattr(book_indexing_service.settings, "VOYAGE_EMBED_BATCH_SIZE", 32)
    monkeypatch.setattr(book_indexing_service.settings, "VOYAGE_EMBED_BATCH_DELAY_SECONDS", 0)

    marked: list = []

    def fake_mark(updates):
        marked.extend(updates)
        return len(updates)

    monkeypatch.setattr(book_indexing_service, "mark_chunks_embedded", fake_mark)
    monkeypatch.setattr(book_indexing_service, "mark_chunks_embed_failed", lambda *a, **k: 0)
    monkeypatch.setattr(book_indexing_service, "count_pending_embed_chunks", lambda book_id: 0)

    stats = book_indexing_service.embed_pending_chunks(1)
    assert stats["embedded"] == 2
    assert stats["failed"] == 0
    assert len(marked) == 2


def test_embed_pending_chunks_voyage_error_keeps_text_marked_failed(monkeypatch):
    from app.services import book_indexing_service

    pending = [{"_id": "id1", "embedded_text": "[U]\none", "text": "one", "unit_title": "U"}]

    def fake_fetch(book_id, unit_id=None, limit=32):
        return pending if not getattr(fake_fetch, "called", False) else []

    # only return pending once
    state = {"once": True}

    def fetch_once(book_id, unit_id=None, limit=32):
        if state["once"]:
            state["once"] = False
            return pending
        return []

    monkeypatch.setattr(book_indexing_service, "fetch_pending_embed_chunks", fetch_once)
    monkeypatch.setattr(
        book_indexing_service,
        "embed_texts",
        lambda texts: (_ for _ in ()).throw(RuntimeError("rate limit")),
    )
    monkeypatch.setattr(book_indexing_service.settings, "VOYAGE_EMBED_BATCH_SIZE", 32)
    monkeypatch.setattr(book_indexing_service.settings, "VOYAGE_EMBED_BATCH_DELAY_SECONDS", 0)

    failed_ids: list = []

    def fake_fail(ids, error):
        failed_ids.extend(ids)
        return len(ids)

    monkeypatch.setattr(book_indexing_service, "mark_chunks_embed_failed", fake_fail)
    monkeypatch.setattr(book_indexing_service, "mark_chunks_embedded", lambda updates: 0)
    monkeypatch.setattr(book_indexing_service, "count_pending_embed_chunks", lambda book_id: 1)

    stats = book_indexing_service.embed_pending_chunks(1)
    assert stats["embedded"] == 0
    assert stats["failed"] == 1
    assert failed_ids == ["id1"]


def test_index_unit_chunks_raises_on_empty_text(tmp_path: Path):
    from pypdf import PdfWriter

    path = tmp_path / "blank.pdf"
    writer = PdfWriter()
    writer.add_blank_page(612, 792)
    with path.open("wb") as handle:
        writer.write(handle)

    unit = SimpleNamespace(id=1, unit_index=0, title="Empty", page_start=1, page_end=1)
    book = SimpleNamespace(
        id=1,
        book_type=BookTypeEnum.freeform,
        cefr_level=None,
        detection_method="toc",
    )

    with pytest.raises(ValueError, match="empty"):
        index_unit_chunks(book, unit, str(path))
