from app.services.skill_drill_align import (
    align_score,
    batch_align_ratio,
    expand_surfaces,
)


def test_align_score_finds_surface_in_stem():
    assert align_score(
        {
            "stem": "Choose: The store ___ big.",
            "answer": "is",
            "options": ["am", "is", "are"],
        },
        {"is", "are"},
    )


def test_align_score_false_when_missing():
    assert not align_score(
        {
            "stem": "What year was HBC founded?",
            "answer": "1670",
            "options": [],
            "passage": "A long story",
        },
        {"am", "is", "are"},
    )


def test_align_score_false_when_surface_inside_longer_word():
    assert not align_score(
        {"stem": "Canadian history", "answer": "x", "options": []},
        {"is"},
    )


def test_batch_ratio():
    items = [
        {"stem": "I ___ a student", "answer": "am", "options": ["am", "is"]},
        {"stem": "Unrelated reading trivia", "answer": "x", "options": []},
    ]
    assert batch_align_ratio(items, {"am"}) == 0.5


def test_expand_surfaces_adds_article_from_np():
    assert expand_surfaces({"a student", "an apple"}) >= {"a", "an", "a student", "an apple"}


def test_align_article_cloze_via_bare_determiner():
    # Pack targets are NPs; cloze blanks the article so the full phrase is gone.
    assert align_score(
        {
            "stem": "Please give me ____ pen.",
            "answer": "a",
            "options": [],
        },
        {"a pen", "an eraser"},
    )


def test_align_bare_a_requires_answer_not_stem():
    assert not align_score(
        {
            "stem": "A long story about Canada.",
            "answer": "1670",
            "options": ["1670", "1770"],
        },
        {"a"},
    )
    assert align_score(
        {"stem": "Choose the article.", "answer": "a", "options": ["a", "an"]},
        {"a"},
    )
