import re

import pdfplumber

from app.services.book_structure.base import DetectedUnit, DetectionResult, StructureDetector

REGEX_CONFIDENCE = 0.6
DENSE_PAGE_MATCH_THRESHOLD = 2

# (pattern, source label, priority) — higher priority = more specific chunk unit
PATTERN_SPECS: list[tuple[re.Pattern[str], str, int]] = [
    # PASSAGE / PASSSAGE / Passage 1: ... (tolerate common OCR/typo extra S)
    (re.compile(r"^PASS+AGE\s*\d+\s*[:.\-–—]?", re.IGNORECASE), "passage", 100),
    (re.compile(r"^(TEST|Test)\s*\d+\b"), "test", 80),
    # Unit/Chapter/Section with optional colon title
    (re.compile(r"^(Unit|Chapter|Section|Part)\s+\d+\s*[:.\-–—]?", re.IGNORECASE), "section", 60),
    (re.compile(r"^(Bài|Chương|Phần)\s+\d+\b"), "section_vi", 60),
]


def _extract_heading_lines(page_text: str) -> list[str]:
    lines = []
    for raw_line in page_text.splitlines():
        line = raw_line.strip()
        if line:
            lines.append(line)
    return lines


def _match_line(line: str) -> tuple[str, str] | None:
    """Return (source, original_line) if line matches a heading pattern."""
    for pattern, source, _priority in PATTERN_SPECS:
        if pattern.match(line):
            return source, line
    return None


def _find_matches(page_texts: list[str]) -> dict[str, list[tuple[int, str]]]:
    """Return {source: [(page_number_1based, title_line), ...]} after filtering dense TOC pages."""
    source_priority = {source: priority for _pat, source, priority in PATTERN_SPECS}
    matches: dict[str, list[tuple[int, str]]] = {}

    for page_number, page_text in enumerate(page_texts, start=1):
        if not page_text:
            continue
        page_hits: list[tuple[str, str]] = []
        for line in _extract_heading_lines(page_text):
            matched = _match_line(line)
            if matched:
                page_hits.append(matched)
        if not page_hits:
            continue

        kept_hits = _filter_page_hits(page_hits, source_priority)
        for source, title in kept_hits:
            matches.setdefault(source, []).append((page_number, title))
    return matches


def _filter_page_hits(
    page_hits: list[tuple[str, str]],
    source_priority: dict[str, int],
) -> list[tuple[str, str]]:
    """Drop TOC/overview pages; keep best heading when TEST+PASSAGE share a page."""
    if len(page_hits) < DENSE_PAGE_MATCH_THRESHOLD:
        return page_hits

    sources = {source for source, _title in page_hits}
    # Many same-source headings on one page => TOC / Section Overview.
    if len(sources) == 1:
        return []

    # Mixed sources (e.g. TEST + PASSAGE): keep highest-priority source only.
    best_source = max(sources, key=lambda source: source_priority.get(source, 0))
    for source, title in page_hits:
        if source == best_source:
            return [(source, title)]
    return []


def _pick_best_source(matches: dict[str, list[tuple[int, str]]]) -> str | None:
    if not matches:
        return None

    source_priority = {source: priority for _pat, source, priority in PATTERN_SPECS}
    return max(
        matches.keys(),
        key=lambda source: (len(matches[source]), source_priority.get(source, 0)),
    )


def _build_units(headings: list[tuple[int, str]], total_pages: int) -> list[DetectedUnit]:
    headings.sort(key=lambda item: item[0])
    # Keep first heading per page to avoid duplicate Unit/Chapter on same page.
    deduped: list[tuple[int, str]] = []
    seen_pages: set[int] = set()
    for page_start, title in headings:
        if page_start in seen_pages:
            continue
        seen_pages.add(page_start)
        deduped.append((page_start, title))

    units: list[DetectedUnit] = []
    for index, (page_start, title) in enumerate(deduped):
        if index + 1 < len(deduped):
            page_end = deduped[index + 1][0] - 1
        else:
            page_end = total_pages
        if page_end < page_start:
            page_end = page_start
        units.append(
            DetectedUnit(
                title=title,
                page_start=page_start,
                page_end=page_end,
                depth_or_source="regex",
            )
        )
    return units


class RegexDetector(StructureDetector):
    name = "regex"

    def detect(self, pdf_path: str) -> DetectionResult | None:
        page_texts: list[str] = []
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                page_texts.append(page.extract_text() or "")

        if not page_texts:
            return None

        matches = _find_matches(page_texts)
        best_source = _pick_best_source(matches)
        if not best_source:
            return None

        headings = matches[best_source]
        if len(headings) < 2:
            return None

        units = _build_units(headings, len(page_texts))
        if len(units) < 2:
            return None

        return DetectionResult(method=self.name, confidence=REGEX_CONFIDENCE, units=units)
