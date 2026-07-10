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


class FontStyleDetector(StructureDetector):
    name = "font_style"

    def detect(self, pdf_path: str) -> DetectionResult | None:
        headings: list[tuple[int, str]] = []
        all_sizes: list[float] = []

        with pdfplumber.open(pdf_path) as pdf:
            for page_number, page in enumerate(pdf.pages, start=1):
                line_info = _line_font_sizes(page)
                for _text, size, _bold in line_info:
                    if size > 0:
                        all_sizes.append(size)

            if not all_sizes:
                return None

            try:
                body_size = float(mode(all_sizes))
            except StatisticsError:
                body_size = Counter(round(s, 1) for s in all_sizes).most_common(1)[0][0]

            threshold = body_size * HEADING_SIZE_RATIO

            for page_number, page in enumerate(pdf.pages, start=1):
                for text, size, is_bold in _line_font_sizes(page):
                    if len(text) < 3:
                        continue
                    if size >= threshold or is_bold:
                        headings.append((page_number, text))

        if len(headings) < 2:
            return None

        headings.sort(key=lambda item: item[0])
        units: list[DetectedUnit] = []
        with pdfplumber.open(pdf_path) as pdf:
            total_pages = len(pdf.pages)

        for index, (page_start, title) in enumerate(headings):
            page_end = headings[index + 1][0] - 1 if index + 1 < len(headings) else total_pages
            units.append(
                DetectedUnit(
                    title=title,
                    page_start=page_start,
                    page_end=page_end,
                    depth_or_source="font",
                )
            )

        return DetectionResult(method=self.name, confidence=FONT_CONFIDENCE, units=units)
