"""Merge heuristic structure candidates with an LLM review of skimmed PDF text."""

from __future__ import annotations

import json
import logging
import re
from typing import Any

import pdfplumber

from app.core.config import settings
from app.services.book_structure.base import DetectedUnit, DetectionResult
from app.services.llm_client import chat_json

logger = logging.getLogger(__name__)

AI_MERGE_CONFIDENCE = 0.85

# Answer keys, glossaries, appendix back-matter — not learning units.
BACK_MATTER_UNIT_RE = re.compile(
    r"(?:"
    r"\banswers?\b|"
    r"\bdefinitions?\b|"
    r"\banswer\s*key\b|"
    r"\bkey\s+to\s+(?:the\s+)?exercises?\b|"
    r"\bglossary\b|"
    r"\bindex\b|"
    r"\bappendix\b"
    r")",
    re.IGNORECASE,
)

SYSTEM_PROMPT = """You are an ESL/PDF book structure referee.
You receive multiple detector proposals and skimmed text from the start of each page.
Return ONE cleaned unit list as JSON:
{"units":[{"title":str,"page_start":int,"page_end":int}]}

Rules:
- Prefer selecting/editing units from detector proposals.
- Only add a unit when its heading appears in the skim text.
- Drop accessibility / contents / index junk (Images, Links, Accessibility Statement, etc.).
- Drop back-matter / non-lesson sections entirely, including titles like:
  "Chapter N: Answers", "Chapter N: Definitions", "Answer key", "Key to exercises",
  "Glossary", "Index", "Appendix". Do not emit these as units; stop the unit list
  before answer keys and definition lists begin.
- Keep real teaching chapters/units/passages only (lesson content).
- page_start/page_end are 1-based; units must be ordered by page_start.
- For all but the last unit, page_end should be next.page_start - 1.
- Last teaching unit page_end must be where that lesson ends — NOT the last page of the PDF
  if Answers/Definitions/index follow. Leave back-matter pages out of every unit.
- Titles should be concise headings as they appear in the book.
"""


def is_back_matter_unit_title(title: str) -> bool:
    return bool(BACK_MATTER_UNIT_RE.search(title.strip()))


def drop_back_matter_units(units: list[DetectedUnit]) -> list[DetectedUnit]:
    return [u for u in units if not is_back_matter_unit_title(u.title)]


def skim_pdf_headings(
    pdf_path: str,
    *,
    lines_per_page: int | None = None,
    max_pages: int | None = None,
) -> list[str]:
    """Return per-page text truncated to the first N non-empty lines."""
    lines_per_page = lines_per_page if lines_per_page is not None else settings.STRUCTURE_SKIM_LINES_PER_PAGE
    max_pages = max_pages if max_pages is not None else settings.STRUCTURE_SKIM_MAX_PAGES

    page_texts: list[str] = []
    with pdfplumber.open(pdf_path) as pdf:
        for index, page in enumerate(pdf.pages):
            if index >= max_pages:
                break
            raw = page.extract_text() or ""
            kept: list[str] = []
            for line in raw.splitlines():
                line = line.strip()
                if not line:
                    continue
                kept.append(line)
                if len(kept) >= lines_per_page:
                    break
            page_texts.append("\n".join(kept))
    return page_texts


def _candidates_payload(candidates: list[DetectionResult]) -> list[dict[str, Any]]:
    payload: list[dict[str, Any]] = []
    for result in candidates:
        payload.append(
            {
                "method": result.method,
                "confidence": result.confidence,
                "units": [
                    {
                        "title": u.title,
                        "page_start": u.page_start,
                        "page_end": u.page_end,
                        "depth_or_source": u.depth_or_source,
                    }
                    for u in result.units
                ],
            }
        )
    return payload


def _require_raw_units(data: Any) -> list[Any]:
    if not isinstance(data, dict):
        raise ValueError("AI merge response must be a JSON object")
    raw_units = data.get("units")
    if not isinstance(raw_units, list) or not raw_units:
        raise ValueError("AI merge response missing units[]")
    return raw_units


def _parse_raw_units(raw_units: list[Any], total_pages: int) -> list[DetectedUnit]:
    """Build clamped DetectedUnits from raw items; skip title-less, raise on bad pages."""
    units: list[DetectedUnit] = []
    for item in raw_units:
        if not isinstance(item, dict):
            continue
        title = str(item.get("title") or "").strip()
        try:
            page_start = int(item["page_start"])
            page_end = int(item.get("page_end") or page_start)
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError(f"Invalid unit pages in AI merge: {item!r}") from exc
        if not title:
            continue
        page_start = max(1, min(page_start, total_pages))
        page_end = max(page_start, min(page_end, total_pages))
        units.append(
            DetectedUnit(
                title=title,
                page_start=page_start,
                page_end=page_end,
                depth_or_source="ai_merge",
            )
        )

    if not units:
        raise ValueError("AI merge produced no valid units")
    return units


def _assign_page_ranges(units: list[DetectedUnit]) -> list[DetectedUnit]:
    """Order units, drop back-matter, and cap page_end before the next unit / back-matter."""
    units.sort(key=lambda u: u.page_start)
    # If Answers/Definitions follow teaching units, cap the last lesson before them.
    first_back_matter_start = next(
        (u.page_start for u in units if is_back_matter_unit_title(u.title)), None
    )

    units = drop_back_matter_units(units)
    if not units:
        raise ValueError("AI merge produced only back-matter units (Answers/Definitions/etc.)")

    # Middle units: end just before the next unit. Last unit: keep its own end
    # (optionally capped before dropped back-matter) — never force total_pages.
    for index, unit in enumerate(units):
        if index + 1 < len(units):
            unit.page_end = max(unit.page_start, units[index + 1].page_start - 1)
        else:
            end = unit.page_end
            if first_back_matter_start is not None:
                end = min(end, first_back_matter_start - 1)
            unit.page_end = max(unit.page_start, end)
    return units


def _parse_units(data: Any, total_pages: int) -> list[DetectedUnit]:
    raw_units = _require_raw_units(data)
    units = _parse_raw_units(raw_units, total_pages)
    return _assign_page_ranges(units)


def _skim_for_prompt(pdf_path: str, total_pages: int) -> list[dict[str, Any]]:
    """Skim page headings, pad up to the page cap, and keep only non-empty pages."""
    skim = skim_pdf_headings(pdf_path)
    while len(skim) < total_pages and len(skim) < settings.STRUCTURE_SKIM_MAX_PAGES:
        skim.append("")
    return [
        {"page": i + 1, "text": text} for i, text in enumerate(skim[:total_pages]) if text.strip()
    ]


def _build_user_message(
    candidates: list[DetectionResult], skim_for_prompt: list[dict[str, Any]], total_pages: int
) -> str:
    user_payload = {
        "total_pages": total_pages,
        "candidates": _candidates_payload(candidates),
        "page_skims": skim_for_prompt,
    }
    return (
        "Merge these detector candidates into one structure for the book.\n"
        f"{json.dumps(user_payload, ensure_ascii=False)}"
    )


def merge_structure_with_ai(
    pdf_path: str,
    candidates: list[DetectionResult],
    *,
    total_pages: int,
) -> DetectionResult:
    skim_for_prompt = _skim_for_prompt(pdf_path, total_pages)
    user = _build_user_message(candidates, skim_for_prompt, total_pages)

    data = chat_json(SYSTEM_PROMPT, user)
    units = _parse_units(data, total_pages)
    return DetectionResult(method="ai_merge", confidence=AI_MERGE_CONFIDENCE, units=units)
