"""Sync book structure units into canonical learning_skills + book_skill_sources."""

from __future__ import annotations

import logging
import re
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.book import BookDB
from app.models.book_skill_source import BookSkillSourceDB
from app.models.book_structure_preview import BookStructurePreviewDB
from app.models.enums import BookStatusEnum, BookTypeEnum, CEFRLevel, SkillTypeEnum
from app.models.learning_skill import LearningSkillDB, SkillEdgeDB
from app.services.skill_graph_difficulty import difficulty_from_unit_index
from app.services.skill_graph_llm_service import refine_units_with_llm
from app.services.skill_normalize_service import normalize_unit_to_slug

logger = logging.getLogger(__name__)

EXCLUDE_PATTERNS = re.compile(
    r"(answer\s*key|key to exercises|key to additional|study\s*guide|appendix|index|^contents$)",
    re.I,
)

EXISTING_SKILLS_CAP = 200


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


def build_linear_edges(nodes: list[dict[str, Any]]) -> list[tuple[int, int]]:
    """Link consecutive non-excluded nodes by id (skip excluded)."""
    active = [c for c in sorted(nodes, key=lambda x: x["unit_index"]) if not c["is_excluded"]]
    return [(active[i]["id"], active[i + 1]["id"]) for i in range(len(active) - 1)]


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


def _parse_skill_type(raw: str, fallback: SkillTypeEnum) -> SkillTypeEnum:
    try:
        return SkillTypeEnum(str(raw).strip().lower())
    except ValueError:
        return fallback


def build_rule_unit_mappings(
    units: list[dict[str, Any]],
    *,
    default_skill_type: SkillTypeEnum,
) -> list[dict[str, Any]]:
    """Rule-based mappings used when LLM refine fails."""
    n_units = len(units)
    mappings: list[dict[str, Any]] = []
    for u in units:
        slug, display_title = normalize_unit_to_slug(str(u.get("title") or ""))
        unit_index = int(u["unit_index"])
        mappings.append(
            {
                "unit_index": unit_index,
                "slug": slug,
                "title": display_title,
                "skill_type": default_skill_type.value,
                "difficulty_in_level": difficulty_from_unit_index(unit_index, n_units),
                "exclude": should_exclude_unit(str(u.get("title") or "")),
            }
        )
    return mappings


async def _get_or_create_skill(
    db: AsyncSession,
    *,
    slug: str,
    title: str,
    cefr_level: CEFRLevel,
    skill_type: SkillTypeEnum,
    difficulty_in_level: int | None = None,
    overwrite_difficulty: bool = False,
) -> LearningSkillDB:
    existing = (
        await db.execute(
            select(LearningSkillDB).where(
                LearningSkillDB.slug == slug,
                LearningSkillDB.cefr_level == cefr_level,
            )
        )
    ).scalar_one_or_none()
    if existing is not None:
        if difficulty_in_level is not None and (
            overwrite_difficulty or existing.difficulty_in_level is None
        ):
            existing.difficulty_in_level = int(difficulty_in_level)
        return existing

    skill = LearningSkillDB(
        slug=slug,
        title=title,
        cefr_level=cefr_level,
        skill_type=skill_type,
        difficulty_in_level=difficulty_in_level if difficulty_in_level is not None else 5,
        is_active=True,
    )
    db.add(skill)
    await db.flush()
    return skill


async def _load_existing_skills_for_level(
    db: AsyncSession, cefr_level: CEFRLevel
) -> list[dict[str, Any]]:
    rows = list(
        (
            await db.execute(
                select(LearningSkillDB)
                .where(
                    LearningSkillDB.cefr_level == cefr_level,
                    LearningSkillDB.is_active.is_(True),
                )
                .order_by(LearningSkillDB.id)
                .limit(EXISTING_SKILLS_CAP)
            )
        )
        .scalars()
        .all()
    )
    return [
        {
            "slug": s.slug,
            "title": s.title,
            "difficulty_in_level": int(s.difficulty_in_level)
            if s.difficulty_in_level is not None
            else 5,
        }
        for s in rows
    ]


async def _resolve_skill_id(
    db: AsyncSession,
    *,
    slug: str,
    cefr_level: CEFRLevel,
    cache: dict[str, int],
) -> int | None:
    if slug in cache:
        return cache[slug]
    row = (
        await db.execute(
            select(LearningSkillDB).where(
                LearningSkillDB.slug == slug,
                LearningSkillDB.cefr_level == cefr_level,
            )
        )
    ).scalar_one_or_none()
    if row is None:
        return None
    cache[slug] = int(row.id)
    return int(row.id)


async def _add_edge_if_missing(
    db: AsyncSession, from_skill_id: int, to_skill_id: int
) -> bool:
    if from_skill_id == to_skill_id:
        return False
    exists = (
        await db.execute(
            select(SkillEdgeDB).where(
                SkillEdgeDB.from_skill_id == from_skill_id,
                SkillEdgeDB.to_skill_id == to_skill_id,
            )
        )
    ).scalar_one_or_none()
    if exists is not None:
        return False
    db.add(
        SkillEdgeDB(
            from_skill_id=from_skill_id,
            to_skill_id=to_skill_id,
            relation="prerequisite",
        )
    )
    return True


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


def _unit_dicts(units: list[BookStructurePreviewDB]) -> list[dict[str, Any]]:
    return [
        {
            "id": u.id,
            "title": u.title,
            "unit_index": u.unit_index,
            "depth_or_source": u.depth_or_source,
        }
        for u in units
    ]


async def _resolve_mappings(
    db: AsyncSession,
    *,
    book: BookDB,
    book_id: int,
    unit_dicts: list[dict[str, Any]],
    default_skill_type: SkillTypeEnum,
) -> tuple[list[dict[str, Any]], list[tuple[str, str]], bool]:
    """LLM refine first; rule fallback on any failure."""
    cefr_value = (
        book.cefr_level.value if hasattr(book.cefr_level, "value") else str(book.cefr_level)
    )
    llm_input_units = [
        {
            "unit_index": int(u["unit_index"]),
            "title": u["title"],
            "rule_slug": normalize_unit_to_slug(str(u["title"]))[0],
        }
        for u in unit_dicts
    ]
    existing_skills = await _load_existing_skills_for_level(db, book.cefr_level)

    try:
        mappings, prereq_pairs = refine_units_with_llm(
            cefr_level=cefr_value,
            book_title=book.title,
            existing_skills=existing_skills,
            units=llm_input_units,
        )
        return mappings, prereq_pairs, True
    except Exception:
        logger.exception(
            "LLM skill graph refine failed for book_id=%s; falling back to rules",
            book_id,
        )
        return (
            build_rule_unit_mappings(unit_dicts, default_skill_type=default_skill_type),
            [],
            False,
        )


async def _create_sources_from_mappings(
    db: AsyncSession,
    *,
    book: BookDB,
    book_id: int,
    mappings: list[dict[str, Any]],
    units_by_index: dict[int, BookStructurePreviewDB],
    unit_dicts: list[dict[str, Any]],
    default_skill_type: SkillTypeEnum,
    overwrite_difficulty: bool,
) -> tuple[list[BookSkillSourceDB], list[dict[str, Any]], dict[str, int]]:
    created_sources: list[BookSkillSourceDB] = []
    sequence_for_edges: list[dict[str, Any]] = []
    slug_to_id: dict[str, int] = {}

    for mapping in sorted(mappings, key=lambda m: int(m["unit_index"])):
        unit_index = int(mapping["unit_index"])
        preview = units_by_index.get(unit_index)
        if preview is None:
            continue

        difficulty = max(1, min(10, int(mapping.get("difficulty_in_level") or 5)))
        excluded = bool(mapping.get("exclude", False))
        slug = str(mapping["slug"])
        title = str(mapping.get("title") or slug)
        skill = await _get_or_create_skill(
            db,
            slug=slug,
            title=title,
            cefr_level=book.cefr_level,
            skill_type=_parse_skill_type(
                str(mapping.get("skill_type") or ""), default_skill_type
            ),
            difficulty_in_level=difficulty,
            overwrite_difficulty=overwrite_difficulty,
        )
        slug_to_id[slug] = int(skill.id)

        source = BookSkillSourceDB(
            skill_id=skill.id,
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
            is_excluded=excluded,
            is_primary=False,
        )
        db.add(source)
        created_sources.append(source)
        sequence_for_edges.append(
            {"id": int(skill.id), "unit_index": unit_index, "is_excluded": excluded}
        )

    await db.flush()
    return created_sources, sequence_for_edges, slug_to_id


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


async def _union_prerequisite_edges(
    db: AsyncSession,
    *,
    book: BookDB,
    llm_used: bool,
    prereq_slug_pairs: list[tuple[str, str]],
    sequence_for_edges: list[dict[str, Any]],
    slug_to_id: dict[str, int],
) -> int:
    added = 0
    if llm_used and prereq_slug_pairs:
        for frm_slug, to_slug in prereq_slug_pairs:
            frm_id = await _resolve_skill_id(
                db, slug=frm_slug, cefr_level=book.cefr_level, cache=slug_to_id
            )
            to_id = await _resolve_skill_id(
                db, slug=to_slug, cefr_level=book.cefr_level, cache=slug_to_id
            )
            if frm_id is None or to_id is None:
                continue
            if await _add_edge_if_missing(db, frm_id, to_id):
                added += 1
        return added

    seen: set[tuple[int, int]] = set()
    for frm, to in build_linear_edges(sequence_for_edges):
        if frm == to or (frm, to) in seen:
            continue
        seen.add((frm, to))
        if await _add_edge_if_missing(db, frm, to):
            added += 1
    return added


async def sync_skills_from_preview(
    db: AsyncSession, book_id: int
) -> tuple[list[BookSkillSourceDB], dict[str, Any]]:
    """Replace book_skill_sources for a ready book; upsert learning_skills by (slug, cefr).

    Tries LLM refine once; on failure falls back to rule-based normalize + linear edges.
    Returns (sources, meta) where meta includes llm_used and edge_count_added.
    """
    book, units = await _load_ready_book_and_units(db, book_id)
    unit_dicts = _unit_dicts(units)
    units_by_index = {int(u.unit_index): u for u in units}
    default_skill_type = infer_skill_type(book.book_type)

    mappings, prereq_slug_pairs, llm_used = await _resolve_mappings(
        db,
        book=book,
        book_id=book_id,
        unit_dicts=unit_dicts,
        default_skill_type=default_skill_type,
    )

    await db.execute(delete(BookSkillSourceDB).where(BookSkillSourceDB.book_id == book_id))
    created_sources, sequence_for_edges, slug_to_id = await _create_sources_from_mappings(
        db,
        book=book,
        book_id=book_id,
        mappings=mappings,
        units_by_index=units_by_index,
        unit_dicts=unit_dicts,
        default_skill_type=default_skill_type,
        overwrite_difficulty=llm_used,
    )
    await _recompute_primary_sources(db, created_sources)
    edge_count_added = await _union_prerequisite_edges(
        db,
        book=book,
        llm_used=llm_used,
        prereq_slug_pairs=prereq_slug_pairs,
        sequence_for_edges=sequence_for_edges,
        slug_to_id=slug_to_id,
    )

    await db.commit()
    for source in created_sources:
        await db.refresh(source)
    return created_sources, {"llm_used": llm_used, "edge_count_added": edge_count_added}
