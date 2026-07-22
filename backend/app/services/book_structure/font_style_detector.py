from collections import Counter
from statistics import StatisticsError, mode

import pdfplumber

from app.services.book_structure.base import DetectedUnit, DetectionResult, StructureDetector

FONT_CONFIDENCE = 0.4
HEADING_SIZE_RATIO = 1.3


def _line_font_sizes(page) -> list[tuple[str, float, bool]]:
    """Return [(line_text, max_font_size_on_line, is_bold)]."""
    chars = page.chars
    if not chars:
        return []

    lines: dict[float, list[dict]] = {}
    for char in chars:
        key = round(char.get("top", 0), 1)
        lines.setdefault(key, []).append(char)

    results: list[tuple[str, float, bool]] = []
    for line_chars in lines.values():
        line_chars.sort(key=lambda c: c.get("x0", 0))
        text = "".join(c.get("text", "") for c in line_chars).strip()
        if not text:
            continue
        sizes = [float(c.get("size", 0)) for c in line_chars if c.get("size")]
        if not sizes:
            continue
        max_size = max(sizes)
        is_bold = any("bold" in (c.get("fontname") or "").lower() for c in line_chars)
        results.append((text, max_size, is_bold))
    return results


def _scan_pages(pdf_path: str) -> tuple[list[tuple[int, list[tuple[str, float, bool]]]], int]:
    """Open the PDF once; return [(page_number, line_infos)] and total page count."""
    pages: list[tuple[int, list[tuple[str, float, bool]]]] = []
    with pdfplumber.open(pdf_path) as pdf:
        total_pages = len(pdf.pages)
        for page_number, page in enumerate(pdf.pages, start=1):
            pages.append((page_number, _line_font_sizes(page)))
    return pages, total_pages


def _body_font_size(
    pages: list[tuple[int, list[tuple[str, float, bool]]]],
) -> float | None:
    """Most common line font size (the body text), or None when no sizes exist."""
    all_sizes = [size for _pn, infos in pages for _text, size, _bold in infos if size > 0]
    if not all_sizes:
        return None
    try:
        return float(mode(all_sizes))
    except StatisticsError:
        return Counter(round(s, 1) for s in all_sizes).most_common(1)[0][0]


def _collect_headings(
    pages: list[tuple[int, list[tuple[str, float, bool]]]], threshold: float
) -> list[tuple[int, str]]:
    """Lines that read as headings: large font or bold, and not too short."""
    headings: list[tuple[int, str]] = []
    for page_number, infos in pages:
        for text, size, is_bold in infos:
            if len(text) < 3:
                continue
            if size >= threshold or is_bold:
                headings.append((page_number, text))
    return headings


def _build_units(headings: list[tuple[int, str]], total_pages: int) -> list[DetectedUnit]:
    ordered = sorted(headings, key=lambda item: item[0])
    units: list[DetectedUnit] = []
    for index, (page_start, title) in enumerate(ordered):
        page_end = ordered[index + 1][0] - 1 if index + 1 < len(ordered) else total_pages
        units.append(
            DetectedUnit(
                title=title,
                page_start=page_start,
                page_end=page_end,
                depth_or_source="font",
            )
        )
    return units


class FontStyleDetector(StructureDetector):
    name = "font_style"

    def detect(self, pdf_path: str) -> DetectionResult | None:
        pages, total_pages = _scan_pages(pdf_path)

        body_size = _body_font_size(pages)
        if body_size is None:
            return None

        headings = _collect_headings(pages, body_size * HEADING_SIZE_RATIO)
        if len(headings) < 2:
            return None

        units = _build_units(headings, total_pages)
        return DetectionResult(method=self.name, confidence=FONT_CONFIDENCE, units=units)
