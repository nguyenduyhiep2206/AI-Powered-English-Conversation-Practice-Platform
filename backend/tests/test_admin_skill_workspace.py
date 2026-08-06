from types import SimpleNamespace

from app.services.admin_skill_workspace import (
    BLOCK_GRAMMAR_LESSON,
    BLOCK_NO_BOOK,
    build_lesson_slice,
    compute_quiz_gate,
)


def test_grammar_blocks_without_published_lesson():
    blocked = compute_quiz_gate(
        skill_type="grammar",
        lesson_status="draft",
        has_book_source=True,
        has_lesson_surfaces=True,
    )
    assert blocked.can_generate is False
    assert blocked.block_reason == BLOCK_GRAMMAR_LESSON

    ok = compute_quiz_gate(
        skill_type="grammar",
        lesson_status="published",
        has_book_source=True,
        has_lesson_surfaces=True,
    )
    assert ok.can_generate is True
    assert ok.block_reason is None


def test_grammar_blocks_when_no_surfaces():
    gate = compute_quiz_gate(
        skill_type="grammar",
        lesson_status="published",
        has_book_source=True,
        has_lesson_surfaces=False,
    )
    assert gate.can_generate is False
    assert gate.block_reason == BLOCK_GRAMMAR_LESSON


def test_no_book_source_blocks_all():
    gate = compute_quiz_gate(
        skill_type="vocabulary",
        lesson_status=None,
        has_book_source=False,
    )
    assert gate.can_generate is False
    assert gate.block_reason == BLOCK_NO_BOOK


def test_vocab_ok_without_lesson():
    gate = compute_quiz_gate(
        skill_type="vocabulary",
        lesson_status=None,
        has_book_source=True,
    )
    assert gate.can_generate is True


def test_build_lesson_slice_prefers_published_pack_zero():
    lessons = [
        SimpleNamespace(
            id=1, status="draft", pack_index=0, title="Draft", content={}
        ),
        SimpleNamespace(
            id=2,
            status="published",
            pack_index=0,
            title="L1",
            content={"targets": [{"surface": "was"}]},
        ),
        SimpleNamespace(
            id=3, status="published", pack_index=1, title="L2", content={}
        ),
    ]
    payload, has_surfaces = build_lesson_slice(lessons)  # type: ignore[arg-type]
    assert payload["status"] == "published"
    assert payload["id"] == 2
    assert payload["pack_published_count"] == 2
    assert payload["pack_total"] == 3
    assert has_surfaces is True
