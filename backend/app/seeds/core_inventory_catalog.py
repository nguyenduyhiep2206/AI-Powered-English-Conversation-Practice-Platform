"""Wipe learning_skills and seed A1–C1 Core Inventory catalog from JSONL.

Reads reviewed files under ``app/seeds/core_inventory/`` (skills + within-level
edges + cross-level bridges). Intended for local/dev reset — CASCADE will drop
skill edges, mastery, lesson packs, theme-unit skill links, etc.

Run (from backend / api container):
    python -m app.seeds.core_inventory_catalog --wipe
"""

from __future__ import annotations

import argparse
import asyncio
import json
from collections import Counter
from pathlib import Path
from typing import Any

from sqlalchemy import delete, func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import AsyncSessionLocal
from app.models.enums import CEFRLevel, SkillTypeEnum
from app.models.learning_skill import LearningSkillDB, SkillEdgeDB

INVENTORY_DIR = Path(__file__).resolve().parent / "core_inventory"

SKILL_FILES = [
    "skills.jsonl",  # A1
    "skills_a2.jsonl",
    "skills_b1.jsonl",
    "skills_b2.jsonl",
    "skills_c1.jsonl",
]

EDGE_FILES = [
    "edges.jsonl",  # A1 within-level
    "edges_a2.jsonl",
    "edges_b1.jsonl",
    "edges_b2.jsonl",
    "edges_c1.jsonl",
    "edges_bridge_a2.jsonl",
    "edges_bridge_b1.jsonl",
    "edges_bridge_b2.jsonl",
    "edges_bridge_c1.jsonl",
]


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        raise FileNotFoundError(f"Missing inventory file: {path}")
    rows: list[dict[str, Any]] = []
    for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        line = line.strip()
        if not line:
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError as exc:
            raise ValueError(f"{path.name}:{line_no}: invalid JSON") from exc
    return rows


def load_skills() -> list[dict[str, Any]]:
    skills: list[dict[str, Any]] = []
    seen: set[str] = set()
    for name in SKILL_FILES:
        for raw in _read_jsonl(INVENTORY_DIR / name):
            slug = str(raw["slug"]).strip()
            if slug in seen:
                raise ValueError(f"Duplicate slug across inventory: {slug}")
            seen.add(slug)
            level = CEFRLevel(str(raw["cefr_level"]).strip())
            stype = SkillTypeEnum(str(raw["skill_type"]).strip())
            diff = int(raw["difficulty_in_level"])
            if not 1 <= diff <= 10:
                raise ValueError(f"{slug}: difficulty_in_level out of range: {diff}")
            title = str(raw["title"]).strip()
            if not title or len(title) > 500:
                raise ValueError(f"{slug}: invalid title")
            skills.append(
                {
                    "slug": slug,
                    "title": title,
                    "cefr_level": level,
                    "skill_type": stype,
                    "difficulty_in_level": diff,
                    "is_active": True,
                    "origin": "catalog",
                }
            )
    return skills


def load_edges() -> list[tuple[str, str]]:
    edges: list[tuple[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for name in EDGE_FILES:
        for raw in _read_jsonl(INVENTORY_DIR / name):
            frm = str(raw["from_slug"]).strip()
            to = str(raw["to_slug"]).strip()
            key = (frm, to)
            if key in seen:
                continue
            seen.add(key)
            edges.append(key)
    return edges


async def wipe_all_skills(db: AsyncSession) -> int:
    """Delete every learning_skill row (CASCADE dependents)."""
    before = (
        await db.execute(select(func.count()).select_from(LearningSkillDB))
    ).scalar_one()
    await db.execute(delete(LearningSkillDB))
    await db.flush()
    return int(before)


async def insert_skills(db: AsyncSession, rows: list[dict[str, Any]]) -> int:
    for row in rows:
        stmt = pg_insert(LearningSkillDB).values(**row)
        stmt = stmt.on_conflict_do_update(
            constraint="uq_learning_skill_slug_cefr",
            set_={
                "title": stmt.excluded.title,
                "skill_type": stmt.excluded.skill_type,
                "difficulty_in_level": stmt.excluded.difficulty_in_level,
                "is_active": stmt.excluded.is_active,
                "origin": stmt.excluded.origin,
            },
        )
        await db.execute(stmt)
    await db.flush()
    return len(rows)


async def insert_edges(db: AsyncSession, edges: list[tuple[str, str]]) -> dict[str, int]:
    result = await db.execute(
        select(LearningSkillDB.id, LearningSkillDB.slug).where(
            LearningSkillDB.origin == "catalog"
        )
    )
    slug_to_id = {slug: int(sid) for sid, slug in result.all()}
    added = 0
    skipped_missing = 0
    skipped_self = 0
    for frm_slug, to_slug in edges:
        frm_id = slug_to_id.get(frm_slug)
        to_id = slug_to_id.get(to_slug)
        if frm_id is None or to_id is None:
            skipped_missing += 1
            continue
        if frm_id == to_id:
            skipped_self += 1
            continue
        stmt = pg_insert(SkillEdgeDB).values(
            from_skill_id=frm_id,
            to_skill_id=to_id,
            relation="prerequisite",
        )
        stmt = stmt.on_conflict_do_nothing(constraint="uq_skill_edge")
        res = await db.execute(stmt)
        if res.rowcount:
            added += 1
    await db.flush()
    return {
        "edges_added": added,
        "edges_skipped_missing_slug": skipped_missing,
        "edges_skipped_self": skipped_self,
        "edge_pairs_loaded": len(edges),
    }


async def seed_core_inventory(db: AsyncSession, *, wipe: bool) -> dict[str, Any]:
    skills = load_skills()
    edges = load_edges()
    wiped = 0
    if wipe:
        wiped = await wipe_all_skills(db)

    inserted = await insert_skills(db, skills)
    edge_stats = await insert_edges(db, edges)

    by_level = Counter(s["cefr_level"].value for s in skills)
    active = (
        await db.execute(
            select(func.count()).select_from(LearningSkillDB).where(
                LearningSkillDB.is_active.is_(True),
                LearningSkillDB.origin == "catalog",
            )
        )
    ).scalar_one()
    edge_count = (
        await db.execute(select(func.count()).select_from(SkillEdgeDB))
    ).scalar_one()

    return {
        "wiped_skills": wiped,
        "skills_upserted": inserted,
        "active_catalog_skills": int(active),
        "skill_edges_total": int(edge_count),
        "by_level": dict(by_level),
        **edge_stats,
    }


async def _main(wipe: bool) -> None:
    async with AsyncSessionLocal() as session:
        stats = await seed_core_inventory(session, wipe=wipe)
        await session.commit()
    print("Core Inventory seed complete:")
    for key, val in stats.items():
        print(f"  {key}: {val}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--wipe",
        action="store_true",
        help="Delete ALL learning_skills before seeding (CASCADE dependents).",
    )
    args = parser.parse_args()
    if not args.wipe:
        parser.error("Refusing to run without --wipe (this seed replaces the catalog).")
    asyncio.run(_main(wipe=True))


if __name__ == "__main__":
    main()
