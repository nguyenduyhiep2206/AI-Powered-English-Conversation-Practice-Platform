from app.services.book_structure.detector_chain import StructureDetectorChain
from app.services.book_structure.ai_merge_service import (
    drop_back_matter_units,
    is_back_matter_unit_title,
    merge_structure_with_ai,
)
from app.services.book_structure.base import DetectedUnit


def test_merge_builds_result_from_llm(monkeypatch, numbered_caps_passage_pdf):
    from app.services.book_structure import ai_merge_service as mod

    def fake_chat_json(system, user):
        return {
            "units": [
                {
                    "title": "1. THE OLD MAN WAITS AT THE POST OFFICE",
                    "page_start": 1,
                    "page_end": 1,
                },
                {
                    "title": "2. DON’T WEAR HEADPHONES WHILE DRIVING",
                    "page_start": 2,
                    "page_end": 2,
                },
                {"title": "3. MAX THE CAT", "page_start": 3, "page_end": 3},
            ]
        }

    monkeypatch.setattr(mod, "chat_json", fake_chat_json)
    candidates = StructureDetectorChain().detect_all(str(numbered_caps_passage_pdf))
    result = merge_structure_with_ai(
        str(numbered_caps_passage_pdf), candidates, total_pages=3
    )
    assert result.method == "ai_merge"
    assert len(result.units) == 3
    assert result.units[-1].page_end == 3


def test_back_matter_titles_are_detected():
    assert is_back_matter_unit_title("Chapter 1: Answers")
    assert is_back_matter_unit_title("Chapter 9: Definitions")
    assert is_back_matter_unit_title("Answer key")
    assert not is_back_matter_unit_title("Chapter 1: Present Perfect")


def test_merge_drops_answers_and_definitions(monkeypatch, numbered_caps_passage_pdf):
    from app.services.book_structure import ai_merge_service as mod

    def fake_chat_json(system, user):
        return {
            "units": [
                {"title": "Chapter 1: Present Perfect", "page_start": 1, "page_end": 1},
                {"title": "Chapter 1: Answers", "page_start": 2, "page_end": 2},
                {"title": "Chapter 1: Definitions", "page_start": 3, "page_end": 3},
            ]
        }

    monkeypatch.setattr(mod, "chat_json", fake_chat_json)
    result = merge_structure_with_ai(
        str(numbered_caps_passage_pdf), [], total_pages=3
    )
    assert len(result.units) == 1
    assert result.units[0].title == "Chapter 1: Present Perfect"
    # Must end before Answers (page 2), not stretch to total_pages=3
    assert result.units[0].page_end == 1


def test_last_unit_keeps_own_end_not_total_pages(monkeypatch, numbered_caps_passage_pdf):
    from app.services.book_structure import ai_merge_service as mod

    def fake_chat_json(system, user):
        return {
            "units": [
                {"title": "Chapter 1: Food", "page_start": 1, "page_end": 1},
                {"title": "Chapter 2: Travel", "page_start": 2, "page_end": 2},
            ]
        }

    monkeypatch.setattr(mod, "chat_json", fake_chat_json)
    # PDF fixture has 3 pages; last teaching unit must stay at 2, not become 3
    result = merge_structure_with_ai(
        str(numbered_caps_passage_pdf), [], total_pages=3
    )
    assert len(result.units) == 2
    assert result.units[-1].page_start == 2
    assert result.units[-1].page_end == 2


def test_drop_back_matter_units_helper():
    kept = drop_back_matter_units(
        [
            DetectedUnit("Unit 1: Food", 1, 10),
            DetectedUnit("Chapter 2: Answers", 11, 12),
            DetectedUnit("Chapter 3: Definitions", 13, 14),
        ]
    )
    assert [u.title for u in kept] == ["Unit 1: Food"]
