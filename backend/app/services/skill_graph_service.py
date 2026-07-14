"""Sync book structure units into canonical learning_skills + book_skill_sources."""

from __future__ import annotations

import re
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.book import BookDB
from app.models.book_skill_source import BookSkillSourceDB
from app.models.book_structure_preview import BookStructurePreviewDB
from app.models.enums import BookStatusEnum, BookTypeEnum, CEFRLevel, SkillTypeEnum
from app.models.learning_skill import LearningSkillDB, SkillEdgeDB
from app.services.skill_normalize_service import normalize_unit_to_slug

EXCLUDE_PATTERNS = re.compile(
    r"(answer\s*key|key to exercises|key to additional|study\s*guide|appendix|index|^contents$)",
    re.I,
)


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


async def _get_or_create_skill(
    db: AsyncSession,
    *,
    slug: str,
    title: str,
    cefr_level: CEFRLevel,
    skill_type: SkillTypeEnum,
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
        return existing

    skill = LearningSkillDB(
        slug=slug,
        title=title,
        cefr_level=cefr_level,
        skill_type=skill_type,
        is_active=True,
    )
    db.add(skill)
    await db.flush()
    return skill


async def sync_skills_from_preview(db: AsyncSession, book_id: int) -> list[BookSkillSourceDB]:
    """Replace book_skill_sources for a ready book; upsert learning_skills by (slug, cefr)."""
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

    unit_dicts = [
        {
            "id": u.id,
            "title": u.title,
            "unit_index": u.unit_index,
            "depth_or_source": u.depth_or_source,
        }
        for u in units
    ]

    # Remove previous sources/edges tied to this book's active skills chain markers.
    await db.execute(delete(BookSkillSourceDB).where(BookSkillSourceDB.book_id == book_id))
    skill_type = infer_skill_type(book.book_type)
    created_sources: list[BookSkillSourceDB] = []
    sequence_for_edges: list[dict[str, Any]] = []

    for u in units:
        excluded = should_exclude_unit(u.title)
        slug, display_title = normalize_unit_to_slug(u.title)
        skill = await _get_or_create_skill(
            db,
            slug=slug,
            title=display_title,
            cefr_level=book.cefr_level,
            skill_type=skill_type,
        )
        source = BookSkillSourceDB(
            skill_id=skill.id,
            book_id=book_id,
            unit_id=u.id,
            unit_title=u.title,
            section_title=infer_section_title(
                {
                    "title": u.title,
                    "unit_index": u.unit_index,
                    "depth_or_source": u.depth_or_source,
                },
                unit_dicts,
            ),
            is_excluded=excluded,
            is_primary=False,
        )
        db.add(source)
        created_sources.append(source)
        sequence_for_edges.append(
            {
                "id": skill.id,
                "unit_index": u.unit_index,
                "is_excluded": excluded,
            }
        )

    await db.flush()

    # Choose primary source per skill across *all* sources for that skill (incl. other books).
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
        best_source, best_book = min(
            all_sources,
            key=lambda row: (_primary_rank(row[1].book_type), row[0].id),
        )
        for source, _book in all_sources:
            source.is_primary = source.id == best_source.id

    # Add prerequisite edges between consecutive non-excluded skills in this book order,
    # skipping duplicate consecutive skill ids and existing edges.
    pairs = build_linear_edges(sequence_for_edges)
    seen_pairs: set[tuple[int, int]] = set()
    for frm, to in pairs:
        if frm == to or (frm, to) in seen_pairs:
            continue
        seen_pairs.add((frm, to))
        exists = (
            await db.execute(
                select(SkillEdgeDB).where(
                    SkillEdgeDB.from_skill_id == frm,
                    SkillEdgeDB.to_skill_id == to,
                )
            )
        ).scalar_one_or_none()
        if exists is None:
            db.add(
                SkillEdgeDB(
                    from_skill_id=frm,
                    to_skill_id=to,
                    relation="prerequisite",
                )
            )

    await db.commit()
    for source in created_sources:
        await db.refresh(source)
    return created_sources
