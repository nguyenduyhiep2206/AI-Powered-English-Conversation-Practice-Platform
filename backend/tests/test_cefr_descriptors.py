"""Unit tests for CEFR can-do descriptors and quiz blueprints."""

from app.models.enums import BookTypeEnum, CEFRLevel, SkillTypeEnum
from app.services.cefr_descriptors import (
    blueprint_for,
    get_can_do,
    passage_length_range,
)


def test_get_can_do_returns_nonempty_for_each_level_and_skill():
    for level in CEFRLevel:
        for skill in (SkillTypeEnum.reading, SkillTypeEnum.grammar, SkillTypeEnum.vocabulary):
            text = get_can_do(level, skill)
            assert isinstance(text, str)
            assert len(text) > 20
            assert level.value in text or "CEFR" in text or text[0].isupper()


def test_passage_length_range_increases_with_level():
    a1 = passage_length_range(CEFRLevel.A1)
    b1 = passage_length_range(CEFRLevel.B1)
    c1 = passage_length_range(CEFRLevel.C1)
    assert a1[0] < a1[1]
    assert a1[1] <= b1[1]
    assert b1[1] <= c1[1]
    assert a1 == (120, 400)
    assert b1 == (250, 700)
    assert c1[0] >= 400


def test_blueprint_reading_book_mostly_requires_passage():
    items = blueprint_for(BookTypeEnum.reading_practice, SkillTypeEnum.reading, count=8)
    assert len(items) == 8
    assert all("type" in i and "requires_passage" in i and "cefr_focus" in i for i in items)
    assert sum(1 for i in items if i["requires_passage"]) >= 6
    types = {i["type"] for i in items}
    assert "mcq" in types


def test_blueprint_grammar_book_includes_fix_or_cloze():
    items = blueprint_for(BookTypeEnum.grammar_textbook, SkillTypeEnum.grammar, count=8)
    assert len(items) == 8
    assert any(i["type"] in {"cloze", "fix_grammar"} for i in items)
    assert all(i["requires_passage"] for i in items)


def test_blueprint_count_one():
    items = blueprint_for(BookTypeEnum.freeform, SkillTypeEnum.vocabulary, count=1)
    assert len(items) == 1
    assert items[0]["requires_passage"] is True
