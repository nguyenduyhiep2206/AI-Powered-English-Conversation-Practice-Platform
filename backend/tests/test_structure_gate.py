from app.services.book_structure.base import DetectedUnit
from app.services.book_structure.structure_gate import validate_structure


def test_gate_rejects_empty():
    ok, reasons = validate_structure([], total_pages=10, page_texts=[""] * 10)
    assert ok is False
    assert reasons


def test_gate_accepts_grounded_units():
    pages = ["1\nTHE OLD MAN WAITS\nbody", "more body", "3\nMAX THE CAT\nbody"]
    units = [
        DetectedUnit("1. THE OLD MAN WAITS", 1, 2),
        DetectedUnit("3. MAX THE CAT", 3, 3),
    ]
    ok, reasons = validate_structure(units, total_pages=3, page_texts=pages)
    assert ok is True
    assert reasons == []


def test_gate_rejects_ungrounded_title():
    pages = ["hello world only", "page two"]
    units = [
        DetectedUnit("Chapter 99 Not Real", 1, 1),
        DetectedUnit("Also Fake", 2, 2),
    ]
    ok, _ = validate_structure(units, total_pages=2, page_texts=pages)
    assert ok is False


def test_gate_rejects_junk_majority():
    pages = ["Images here", "Links here", "body three", "body four"]
    units = [
        DetectedUnit("Images", 1, 1),
        DetectedUnit("Links", 2, 2),
        DetectedUnit("Accessibility Statement", 3, 4),
    ]
    ok, reasons = validate_structure(units, total_pages=4, page_texts=pages)
    assert ok is False
    assert any("junk" in r for r in reasons)
