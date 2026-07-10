import re
from statistics import mean
from typing import Any

from pypdf import PdfReader

from app.services.book_structure.base import DetectedUnit, DetectionResult, StructureDetector

# Prefer content-like outline titles over front-matter.
CONTENT_TITLE_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"^\d+\.\d+\s"),  # 1.1 Present Perfect
    re.compile(r"^(Chapter|Unit|Section|Part)\s+\d+\b", re.IGNORECASE),
    re.compile(r"^(Chương|Bài|Phần)\s+\d+\b"),
]

FRONT_MATTER_RE = re.compile(
    r"^(cover|title|copyright|dedication|contents|table of contents|"
    r"list of (figures|tables)|preface|acknowledg|foreword|introduction|"
    r"about the author|index|bibliography|glossary)\b",
    re.IGNORECASE,
)

MIN_HEADINGS_PER_DEPTH = 2
MIN_UNITS_FOR_HIGH_CONFIDENCE = 3
TOC_CONFIDENCE = 0.95
# Prefer depths whose average unit span is in a "chapter-sized" range.
MIN_REASONABLE_AVG_SPAN = 2.0
MAX_REASONABLE_AVG_SPAN = 80.0


def _flatten_outline(outline: Any, reader: PdfReader, depth: int = 0) -> list[dict[str, Any]]:
    if not outline:
        return []

    items: list[dict[str, Any]] = []
    for entry in outline:
        if isinstance(entry, list):
            items.extend(_flatten_outline(entry, reader, depth + 1))
            continue

        title = getattr(entry, "title", None) or getattr(entry, "/Title", None) or str(entry)
        try:
            page_index = reader.get_destination_page_number(entry)
        except Exception:
            continue

        items.append({"title": str(title).strip(), "page_index": page_index, "depth": depth})

        children_attr = getattr(entry, "children", None)
        if children_attr is not None:
            children = children_attr() if callable(children_attr) else children_attr
            if children:
                items.extend(_flatten_outline(list(children), reader, depth + 1))

    return items


def _is_content_title(title: str) -> bool:
    return any(pattern.match(title) for pattern in CONTENT_TITLE_PATTERNS)


def _is_front_matter(title: str) -> bool:
    return bool(FRONT_MATTER_RE.match(title.strip()))


def _avg_page_span(items: list[dict[str, Any]], total_pages: int) -> float:
    if not items:
        return 0.0
    selected = sorted(items, key=lambda item: item["page_index"])
    spans: list[int] = []
    for index, item in enumerate(selected):
        start = item["page_index"] + 1
        if index + 1 < len(selected):
            end = selected[index + 1]["page_index"]
        else:
            end = total_pages
        spans.append(max(1, end - start + 1))
    return float(mean(spans))


def _pick_best_depth(flat_items: list[dict[str, Any]], total_pages: int) -> int | None:
    by_depth: dict[int, list[dict[str, Any]]] = {}
    for item in flat_items:
        by_depth.setdefault(item["depth"], []).append(item)

    # 1) Prefer depths with many content-like titles (Chapter N / N.M / Unit N).
    content_scores: dict[int, int] = {}
    for depth, items in by_depth.items():
        score = sum(1 for item in items if _is_content_title(item["title"]))
        if score >= MIN_HEADINGS_PER_DEPTH:
            content_scores[depth] = score

    if content_scores:
        return max(content_scores.items(), key=lambda pair: pair[1])[0]

    # 2) Fallback: choose depth with reasonable average page span and enough items,
    # preferring fewer front-matter titles.
    candidates: list[tuple[float, int, int, int]] = []
    for depth, items in by_depth.items():
        if len(items) < MIN_UNITS_FOR_HIGH_CONFIDENCE:
            continue
        avg_span = _avg_page_span(items, total_pages)
        if not (MIN_REASONABLE_AVG_SPAN <= avg_span <= MAX_REASONABLE_AVG_SPAN):
            continue
        front_matter_count = sum(1 for item in items if _is_front_matter(item["title"]))
        # Sort key later: fewer front-matter, more items, then closer to mid span.
        span_penalty = abs(avg_span - 10.0)
        candidates.append((front_matter_count, -len(items), span_penalty, depth))

    if candidates:
        candidates.sort()
        return candidates[0][3]

    # 3) Last resort: shallowest depth with enough items (legacy behavior).
    eligible = [d for d, items in by_depth.items() if len(items) >= MIN_UNITS_FOR_HIGH_CONFIDENCE]
    if not eligible:
        return None
    return min(eligible)


def _to_units(flat_items: list[dict[str, Any]], depth: int, total_pages: int) -> list[DetectedUnit]:
    selected = [item for item in flat_items if item["depth"] == depth]
    # If this depth mixes front-matter and chapters, keep content titles when enough remain.
    content_only = [item for item in selected if _is_content_title(item["title"])]
    if len(content_only) >= MIN_HEADINGS_PER_DEPTH:
        selected = content_only

    selected.sort(key=lambda item: item["page_index"])

    units: list[DetectedUnit] = []
    for index, item in enumerate(selected):
        page_start = item["page_index"] + 1
        if index + 1 < len(selected):
            page_end = selected[index + 1]["page_index"]
        else:
            page_end = total_pages
        if page_end < page_start:
            page_end = page_start
        units.append(
            DetectedUnit(
                title=item["title"],
                page_start=page_start,
                page_end=page_end,
                depth_or_source=f"depth={depth}",
            )
        )
    return units


class TocDetector(StructureDetector):
    name = "toc"

    def detect(self, pdf_path: str) -> DetectionResult | None:
        reader = PdfReader(pdf_path)
        outline = reader.outline
        if not outline:
            return None

        flat_items = _flatten_outline(outline, reader)
        if not flat_items:
            return None

        total_pages = len(reader.pages)
        best_depth = _pick_best_depth(flat_items, total_pages)
        if best_depth is None:
            return None

        units = _to_units(flat_items, best_depth, total_pages)
        if len(units) < MIN_HEADINGS_PER_DEPTH:
            return None

        confidence = TOC_CONFIDENCE if len(units) >= MIN_UNITS_FOR_HIGH_CONFIDENCE else 0.7
        return DetectionResult(method=self.name, confidence=confidence, units=units)
