"""Attach book structure units onto curated learning_skills (catalog) + book_skill_sources."""

from __future__ import annotations

import logging
import re
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.book import BookDB
from app.models.book_skill_source import BookSkillSourceDB
from app.models.book_structure_preview import BookStructurePreviewDB
from app.models.enums import BookStatusEnum, BookTypeEnum, CEFRLevel, SkillTypeEnum
from app.models.learning_skill import LearningSkillDB
from app.services.skill_graph_llm_service import attach_units_with_llm
from app.services.skill_normalize_service import normalize_unit_to_slug

logger = logging.getLogger(__name__)

EXCLUDE_PATTERNS = re.compile(
    r"(answer\s*key|key to exercises|key to additional|study\s*guide|appendix|"
    r"index|^contents$|\breview\b|\bprogress\s*check\b|\btest\b|\bexam\b)",
    re.I,
)

CATALOG_SKILLS_CAP = 200


def should_exclude_unit(title: str) -> bool:
    return bool(EXCLUDE_PATTERNS.search(title or ""))


def infer_section_title(unit: dict[str, Any], all_units: list[dict[str, Any]]) -> str | None:
    if (unit.get("depth_or_source") or "").lower() == "section":
        return unit["title"]
    prev_section = None
    for u in sorted(all_units, key=lambda x: x["unit_index"]):
        if u["unit_index"] > unit["unit_index"]:
            break
        if (u.get("depth_or_source") or "").lower() == "section":
            prev_section = u["title"]
    return prev_section


def infer_skill_type(book_type: BookTypeEnum | str | None) -> SkillTypeEnum:
    value = book_type.value if isinstance(book_type, BookTypeEnum) else str(book_type or "")
    if value == BookTypeEnum.grammar_textbook.value:
        return SkillTypeEnum.grammar
    if value == BookTypeEnum.reading_practice.value:
        return SkillTypeEnum.reading
    if value == BookTypeEnum.test_bank.value:
        return SkillTypeEnum.grammar
    return SkillTypeEnum.vocabulary


def _primary_rank(book_type: BookTypeEnum | str | None) -> int:
    """Lower is better when choosing is_primary among sources of the same skill."""
    value = book_type.value if isinstance(book_type, BookTypeEnum) else str(book_type or "")
    order = {
        BookTypeEnum.grammar_textbook.value: 0,
        BookTypeEnum.reading_practice.value: 1,
        BookTypeEnum.test_bank.value: 2,
        BookTypeEnum.freeform.value: 3,
    }
    return order.get(value, 9)


def build_rule_attach_mappings(
    units: list[dict[str, Any]],
    *,
    catalog_slugs: set[str],
) -> list[dict[str, Any]]:
    """Rule fallback: title slug, else first grammar_cue in catalog; else unmapped."""
    catalog = {s.strip().lower() for s in catalog_slugs}
    mappings: list[dict[str, Any]] = []
    for u in units:
        title = str(u.get("title") or "")
        unit_index = int(u["unit_index"])
        if should_exclude_unit(title):
            mappings.append({"unit_index": unit_index, "slug": None, "exclude": True})
            continue
        slug, _display = normalize_unit_to_slug(title)
        if slug in catalog:
            mappings.append({"unit_index": unit_index, "slug": slug, "exclude": False})
            continue
        cue_slug = None
        for cue in u.get("grammar_cues") or []:
            candidate = str(cue).strip().lower()
            if candidate in catalog:
                cue_slug = candidate
                break
        mappings.append(
            {"unit_index": unit_index, "slug": cue_slug, "exclude": False}
        )
    return mappings


def _llm_attach_input_units(unit_dicts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Build attach LLM unit payload: title + enrich signals only (no excerpt/text)."""
    return [
        {
            "unit_index": int(u["unit_index"]),
            "title": u["title"],
            "rule_slug": normalize_unit_to_slug(str(u["title"]))[0],
            "language_focus": u.get("language_focus"),
            "grammar_cues": u.get("grammar_cues") or [],
            "vocab_cues": u.get("vocab_cues") or [],
            "content_summary": u.get("content_summary"),
        }
        for u in unit_dicts
    ]


async def load_catalog_skills(
    db: AsyncSession, cefr_level: CEFRLevel
) -> list[dict[str, Any]]:
    rows = list(
        (
            await db.execute(
                select(LearningSkillDB)
                .where(
                    LearningSkillDB.cefr_level == cefr_level,
                    LearningSkillDB.is_active.is_(True),
                    LearningSkillDB.origin == "catalog",
                )
                .order_by(LearningSkillDB.id)
                .limit(CATALOG_SKILLS_CAP)
            )
        )
        .scalars()
        .all()
    )
    return [
        {
            "id": int(s.id),
            "slug": s.slug,
            "title": s.title,
            "difficulty_in_level": int(s.difficulty_in_level)
            if s.difficulty_in_level is not None
            else 5,
        }
        for s in rows
    ]


async def _load_ready_book_and_units(
    db: AsyncSession, book_id: int
) -> tuple[BookDB, list[BookStructurePreviewDB]]:
    book = (await db.execute(select(BookDB).where(BookDB.id == book_id))).scalar_one_or_none()
    if book is None:
        raise ValueError(f"Không tìm thấy sách {book_id}")
    if book.status != BookStatusEnum.ready:
        raise ValueError("Sách phải ở trạng thái ready trước khi đồng bộ skill graph")
    if book.cefr_level is None:
        raise ValueError("Sách cần cefr_level trước khi đồng bộ skill graph")

    units = list(
        (
            await db.execute(
                select(BookStructurePreviewDB)
                .where(BookStructurePreviewDB.book_id == book_id)
                .order_by(BookStructurePreviewDB.unit_index)
            )
        )
        .scalars()
        .all()
    )
    if not units:
        raise ValueError("Chưa có structure preview — chạy detect-structure trước")
    return book, units


def skill_source_payload(
    source: BookSkillSourceDB, *, skill_title: str
) -> dict[str, Any]:
    return {
        "id": int(source.id),
        "skill_id": int(source.skill_id),
        "skill_title": skill_title,
        "unit_id": int(source.unit_id),
        "unit_title": source.unit_title,
        "section_title": source.section_title,
        "is_excluded": bool(source.is_excluded),
        "is_primary": bool(source.is_primary),
    }


async def _skill_titles_by_id(
    db: AsyncSession, skill_ids: set[int]
) -> dict[int, str]:
    if not skill_ids:
        return {}
    rows = (
        await db.execute(
            select(LearningSkillDB.id, LearningSkillDB.title).where(
                LearningSkillDB.id.in_(skill_ids)
            )
        )
    ).all()
    return {int(skill_id): title for skill_id, title in rows}


async def sources_with_titles(
    db: AsyncSession, sources: list[BookSkillSourceDB]
) -> list[dict[str, Any]]:
    titles = await _skill_titles_by_id(db, {int(s.skill_id) for s in sources})
    return [
        skill_source_payload(
            s,
            skill_title=titles.get(int(s.skill_id), f"#{s.skill_id}"),
        )
        for s in sources
    ]


async def list_book_skill_sources(
    db: AsyncSession, book_id: int
) -> dict[str, Any]:
    """Load persisted attach rows + skill titles; derive unmapped from preview units."""
    book = (
        await db.execute(select(BookDB).where(BookDB.id == book_id))
    ).scalar_one_or_none()
    if book is None:
        raise ValueError(f"Không tìm thấy sách {book_id}")

    units = list(
        (
            await db.execute(
                select(BookStructurePreviewDB)
                .where(BookStructurePreviewDB.book_id == book_id)
                .order_by(BookStructurePreviewDB.unit_index)
            )
        )
        .scalars()
        .all()
    )

    rows = (
        await db.execute(
            select(BookSkillSourceDB, LearningSkillDB.title)
            .join(LearningSkillDB, LearningSkillDB.id == BookSkillSourceDB.skill_id)
            .where(BookSkillSourceDB.book_id == book_id)
            .order_by(BookSkillSourceDB.id)
        )
    ).all()

    sources = [
        skill_source_payload(source, skill_title=title) for source, title in rows
    ]
    sourced_unit_ids = {int(s["unit_id"]) for s in sources}
    # Only derive unmapped after at least one attach row exists for this book.
    unmapped_units = (
        [
            {"unit_index": int(u.unit_index), "unit_title": u.title}
            for u in units
            if int(u.id) not in sourced_unit_ids
        ]
        if sources
        else []
    )
    excluded = sum(1 for s in sources if s["is_excluded"])
    mapped = len(sources) - excluded
    return {
        "book_id": book_id,
        "source_count": len(sources),
        "excluded": excluded,
        "mapped_count": mapped,
        "unmapped_units": unmapped_units,
        "sources": sources,
    }


def _unit_dicts(units: list[BookStructurePreviewDB]) -> list[dict[str, Any]]:
    return [
        {
            "id": u.id,
            "title": u.title,
            "unit_index": u.unit_index,
            "depth_or_source": u.depth_or_source,
            "language_focus": u.language_focus,
            "grammar_cues": u.grammar_cues or [],
            "vocab_cues": u.vocab_cues or [],
            "content_summary": u.content_summary,
        }
        for u in units
    ]


async def _maybe_enrich_units_before_attach(
    db: AsyncSession, book_id: int
) -> dict[str, Any]:
    """Force re-enrich all units before attach; never raises — attach must continue on failure."""
    if not getattr(settings, "UNIT_ENRICH_ENABLED", True):
        return {}
    try:
        from app.services.unit_enrichment_service import enrich_units_for_book

        return await enrich_units_for_book(db, book_id, force=True)
    except Exception:
        logger.exception(
            "Unit enrichment failed for book_id=%s; continuing attach",
            book_id,
        )
        return {"enrichment_incomplete": True}


async def _resolve_attach_mappings(
    db: AsyncSession,
    *,
    book: BookDB,
    book_id: int,
    unit_dicts: list[dict[str, Any]],
    catalog_skills: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], bool]:
    cefr_value = (
        book.cefr_level.value if hasattr(book.cefr_level, "value") else str(book.cefr_level)
    )
    llm_input_units = _llm_attach_input_units(unit_dicts)
    catalog_slugs = {str(s["slug"]) for s in catalog_skills}
    try:
        mappings = attach_units_with_llm(
            cefr_level=cefr_value,
            book_title=book.title,
            catalog_skills=catalog_skills,
            units=llm_input_units,
        )
        return mappings, True
    except Exception:
        logger.exception(
            "LLM attach failed for book_id=%s; falling back to rules",
            book_id,
        )
        return (
            build_rule_attach_mappings(unit_dicts, catalog_slugs=catalog_slugs),
            False,
        )


async def _create_attach_sources(
    db: AsyncSession,
    *,
    book_id: int,
    mappings: list[dict[str, Any]],
    units_by_index: dict[int, BookStructurePreviewDB],
    unit_dicts: list[dict[str, Any]],
    slug_to_skill: dict[str, dict[str, Any]],
) -> tuple[list[BookSkillSourceDB], list[dict[str, Any]], int]:
    """Create sources only for mapped non-excluded units. Returns sources, unmapped, excluded_count."""
    created: list[BookSkillSourceDB] = []
    unmapped: list[dict[str, Any]] = []
    excluded_count = 0

    for mapping in sorted(mappings, key=lambda m: int(m["unit_index"])):
        unit_index = int(mapping["unit_index"])
        preview = units_by_index.get(unit_index)
        if preview is None:
            continue

        if bool(mapping.get("exclude")):
            excluded_count += 1
            continue

        slug = mapping.get("slug")
        if not slug:
            unmapped.append({"unit_index": unit_index, "unit_title": preview.title})
            continue

        skill = slug_to_skill.get(str(slug))
        if skill is None:
            unmapped.append({"unit_index": unit_index, "unit_title": preview.title})
            continue

        source = BookSkillSourceDB(
            skill_id=int(skill["id"]),
            book_id=book_id,
            unit_id=preview.id,
            unit_title=preview.title,
            section_title=infer_section_title(
                {
                    "title": preview.title,
                    "unit_index": preview.unit_index,
                    "depth_or_source": preview.depth_or_source,
                },
                unit_dicts,
            ),
            is_excluded=False,
            is_primary=False,
        )
        db.add(source)
        created.append(source)

    await db.flush()
    return created, unmapped, excluded_count


async def _recompute_primary_sources(
    db: AsyncSession, created_sources: list[BookSkillSourceDB]
) -> None:
    skill_ids = {s.skill_id for s in created_sources if not s.is_excluded}
    for skill_id in skill_ids:
        all_sources = list(
            (
                await db.execute(
                    select(BookSkillSourceDB, BookDB)
                    .join(BookDB, BookDB.id == BookSkillSourceDB.book_id)
                    .where(
                        BookSkillSourceDB.skill_id == skill_id,
                        BookSkillSourceDB.is_excluded.is_(False),
                    )
                )
            ).all()
        )
        if not all_sources:
            continue
        best_source, _best_book = min(
            all_sources,
            key=lambda row: (_primary_rank(row[1].book_type), row[0].id),
        )
        for source, _book in all_sources:
            source.is_primary = source.id == best_source.id


async def _clear_book_sources(db: AsyncSession, book_id: int) -> None:
    await db.execute(delete(BookSkillSourceDB).where(BookSkillSourceDB.book_id == book_id))


async def sync_skills_from_preview(
    db: AsyncSession, book_id: int
) -> tuple[list[BookSkillSourceDB], dict[str, Any]]:
    """Attach book units onto catalog skills; replace this book's book_skill_sources.

    Does not create skills, rewrite edges, or overwrite catalog difficulty.
    Returns (sources, meta) with mapped/unmapped/excluded counts.
    """
    book, units = await _load_ready_book_and_units(db, book_id)
    enrich_meta = await _maybe_enrich_units_before_attach(db, book_id)
    if enrich_meta and not enrich_meta.get("enrichment_incomplete"):
        book, units = await _load_ready_book_and_units(db, book_id)

    unit_dicts = _unit_dicts(units)
    units_by_index = {int(u.unit_index): u for u in units}

    catalog_skills = await load_catalog_skills(db, book.cefr_level)
    if not catalog_skills:
        raise ValueError(
            "No catalog skills for this CEFR level — run: python -m app.seeds.cefr_ladder_a1_a2"
        )

    mappings, llm_used = await _resolve_attach_mappings(
        db,
        book=book,
        book_id=book_id,
        unit_dicts=unit_dicts,
        catalog_skills=catalog_skills,
    )

    await _clear_book_sources(db, book_id)
    slug_to_skill = {str(s["slug"]): s for s in catalog_skills}
    created_sources, unmapped_units, excluded_count = await _create_attach_sources(
        db,
        book_id=book_id,
        mappings=mappings,
        units_by_index=units_by_index,
        unit_dicts=unit_dicts,
        slug_to_skill=slug_to_skill,
    )
    await _recompute_primary_sources(db, created_sources)

    await db.commit()
    for source in created_sources:
        await db.refresh(source)

    return created_sources, {
        "llm_used": llm_used,
        "mapped_count": len(created_sources),
        "unmapped_units": unmapped_units,
        "excluded_count": excluded_count,
        "edge_count_added": 0,
        **enrich_meta,
    }
