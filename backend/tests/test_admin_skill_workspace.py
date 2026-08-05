from app.services.admin_skill_workspace import (
    BLOCK_GRAMMAR_LESSON,
    BLOCK_NO_BOOK,
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
