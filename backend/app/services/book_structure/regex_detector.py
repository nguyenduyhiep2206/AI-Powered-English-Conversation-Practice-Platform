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
    # Numbered ALL-CAPS titles (e.g. Daily Departures: "1" + "THE OLD MAN...")
    (re.compile(r"^\d{1,3}\.\s+[A-Z].{5,}$"), "numbered_caps", 70),
    # Unit/Chapter/Section with optional colon title
    (re.compile(r"^(Unit|Chapter|Section|Part)\s+\d+\s*[:.\-–—]?", re.IGNORECASE), "section", 60),
    (re.compile(r"^(Bài|Chương|Phần)\s+\d+\b"), "section_vi", 60),
]

SOURCE_PRIORITY: dict[str, int] = {source: priority for _pat, source, priority in PATTERN_SPECS}

NUMBER_LINE_RE = re.compile(r"^\d{1,3}$")
# Allow ASCII and curly apostrophes/quotes in ALL-CAPS titles (e.g. DON’T, SAM’S).
ALL_CAPS_TITLE_RE = re.compile(
    r"^[A-Z][A-Z0-9 ,''\u2018\u2019\"\.\-\:\;\!\?/]{6,}$"
)
# Skip question/answer pages that start with a number + short line.
QUESTION_HINT_RE = re.compile(r"^(questions?|answers?|vocabulary)\b", re.IGNORECASE)


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


def _find_numbered_caps_headings(page_texts: list[str]) -> list[tuple[int, str]]:
    """Detect 'N' on one line followed by an ALL-CAPS title on the next line."""
    found: list[tuple[int, str]] = []
    for page_number, page_text in enumerate(page_texts, start=1):
        if not page_text:
            continue
        lines = _extract_heading_lines(page_text)
        for index, line in enumerate(lines):
            if not NUMBER_LINE_RE.match(line):
                continue
            if index + 1 >= len(lines):
                continue
            next_line = lines[index + 1]
            if QUESTION_HINT_RE.match(next_line):
                continue
            if not ALL_CAPS_TITLE_RE.match(next_line):
                continue
            found.append((page_number, f"{line}. {next_line}"))
            break
    return found


def _page_hits(page_text: str) -> list[tuple[str, str]]:
    """All (source, title_line) heading matches on a single page."""
    hits: list[tuple[str, str]] = []
    for line in _extract_heading_lines(page_text):
        matched = _match_line(line)
        if matched:
            hits.append(matched)
    return hits


def _find_matches(page_texts: list[str]) -> dict[str, list[tuple[int, str]]]:
    """Return {source: [(page_number_1based, title_line), ...]} after filtering dense TOC pages."""
    matches: dict[str, list[tuple[int, str]]] = {}

    for page_number, page_text in enumerate(page_texts, start=1):
        if not page_text:
            continue
        kept_hits = _filter_page_hits(_page_hits(page_text))
        for source, title in kept_hits:
            matches.setdefault(source, []).append((page_number, title))

    numbered_caps = _find_numbered_caps_headings(page_texts)
    if len(numbered_caps) >= 2:
        matches["numbered_caps"] = numbered_caps

    return matches


def _filter_page_hits(page_hits: list[tuple[str, str]]) -> list[tuple[str, str]]:
    """Drop TOC/overview pages; keep best heading when TEST+PASSAGE share a page."""
    if len(page_hits) < DENSE_PAGE_MATCH_THRESHOLD:
        return page_hits

    sources = {source for source, _title in page_hits}
    # Many same-source headings on one page => TOC / Section Overview.
    if len(sources) == 1:
        return []

    # Mixed sources (e.g. TEST + PASSAGE): keep highest-priority source only.
    best_source = max(sources, key=lambda source: SOURCE_PRIORITY.get(source, 0))
    for source, title in page_hits:
        if source == best_source:
            return [(source, title)]
    return []


def _pick_best_source(matches: dict[str, list[tuple[int, str]]]) -> str | None:
    if not matches:
        return None
    return max(
        matches.keys(),
        key=lambda source: (len(matches[source]), SOURCE_PRIORITY.get(source, 0)),
    )


def _dedupe_first_per_page(headings: list[tuple[int, str]]) -> list[tuple[int, str]]:
    """Sort by page and keep the first heading per page (avoid same-page duplicates)."""
    deduped: list[tuple[int, str]] = []
    seen_pages: set[int] = set()
    for page_start, title in sorted(headings, key=lambda item: item[0]):
        if page_start in seen_pages:
            continue
        seen_pages.add(page_start)
        deduped.append((page_start, title))
    return deduped


def _build_units(headings: list[tuple[int, str]], total_pages: int) -> list[DetectedUnit]:
    deduped = _dedupe_first_per_page(headings)

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
