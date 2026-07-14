"""Unit tests for packing per-unit chunk text into quiz LLM context."""

from app.services.book_chunk_service import pack_unit_context


def test_pack_unit_context_prefix_dung_khi_het_budget():
    chunks = [
        {"chunk_index": 0, "text": "A" * 100, "_id": "c0"},
        {"chunk_index": 1, "text": "B" * 100, "_id": "c1"},
        {"chunk_index": 2, "text": "C" * 100, "_id": "c2"},
    ]
    text, ids = pack_unit_context(chunks, max_chars=150, mode="prefix")
    assert "A" * 100 in text
    assert set(ids).issubset({"c0", "c1", "c2"})
    assert all(cid in {"c0", "c1"} for cid in ids)


def test_pack_unit_context_stride_lay_dau_giua_cuoi():
    chunks = [
        {"chunk_index": i, "text": f"chunk-{i}-" + ("x" * 20), "_id": f"id{i}"}
        for i in range(10)
    ]
    text, ids = pack_unit_context(chunks, max_chars=5000, mode="stride")
    assert "chunk-0-" in text
    assert "chunk-9-" in text
    assert ("chunk-5-" in text) or ("chunk-4-" in text)


def test_pack_unit_context_rong():
    text, ids = pack_unit_context([], max_chars=5000, mode="prefix")
    assert text == ""
    assert ids == []
