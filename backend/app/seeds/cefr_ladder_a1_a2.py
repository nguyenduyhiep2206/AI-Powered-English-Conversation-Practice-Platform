"""Idempotent seed for curated CEFR A1+A2 skill ladder (catalog).

Books attach content onto these skills; sync must not invent new catalog nodes.

Run:
    python -m app.seeds.cefr_ladder_a1_a2
"""

from __future__ import annotations

import asyncio
from typing import Any

from sqlalchemy import select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import AsyncSessionLocal
from app.models.enums import CEFRLevel, SkillTypeEnum
from app.models.learning_skill import LearningSkillDB, SkillEdgeDB

# (slug, title, difficulty_in_level, skill_type)
A1_SKILLS: list[tuple[str, str, int, str]] = [
    ("be_present", "Verb to be (present)", 1, "grammar"),
    ("subject_pronouns", "Subject pronouns", 1, "grammar"),
    ("articles_a_an_the", "Articles a/an/the (basic)", 2, "grammar"),
    ("this_that_these_those", "This/that/these/those", 2, "grammar"),
    ("possessives", "Possessive adjectives", 3, "grammar"),
    ("have_got", "Have got", 3, "grammar"),
    ("there_is_are", "There is / there are", 3, "grammar"),
    ("present_simple", "Present simple", 4, "grammar"),
    ("present_continuous", "Present continuous", 5, "grammar"),
    ("can_cant", "Can / can't (ability)", 5, "grammar"),
    ("imperatives", "Imperatives", 5, "grammar"),
    ("wh_questions_basic", "Basic Wh- questions", 6, "grammar"),
    ("prepositions_place", "Prepositions of place", 6, "grammar"),
    ("prepositions_time_basic", "Prepositions of time (in/on/at)", 6, "grammar"),
    ("countable_uncountable_basic", "Countable / uncountable (basic)", 7, "grammar"),
    ("some_any", "Some / any", 7, "grammar"),
    ("past_simple_be", "Past simple of be", 8, "grammar"),
    ("past_simple_regular", "Past simple regular verbs", 8, "grammar"),
    ("past_simple_irregular_common", "Past simple common irregulars", 9, "grammar"),
    ("going_to_future", "Going to (future plans)", 9, "grammar"),
    ("everyday_vocab_people", "Everyday vocab: people & jobs", 4, "vocabulary"),
    ("everyday_vocab_places", "Everyday vocab: places & directions", 5, "vocabulary"),
]

A2_SKILLS: list[tuple[str, str, int, str]] = [
    ("present_simple_vs_continuous", "Present simple vs continuous", 2, "grammar"),
    ("past_continuous", "Past continuous", 3, "grammar"),
    ("past_simple_vs_continuous", "Past simple vs continuous", 4, "grammar"),
    ("present_perfect_basic", "Present perfect (experience/just)", 5, "grammar"),
    ("present_perfect_vs_past", "Present perfect vs past simple", 6, "grammar"),
    ("will_future", "Will (predictions/decisions)", 4, "grammar"),
    ("going_to_vs_will", "Going to vs will", 5, "grammar"),
    ("comparatives_superlatives", "Comparatives & superlatives", 3, "grammar"),
    ("quantifiers_much_many", "Quantifiers much/many/a lot of", 3, "grammar"),
    ("modals_should_must", "Should / must (advice/obligation)", 5, "grammar"),
    ("modals_have_to", "Have to / don't have to", 5, "grammar"),
    ("first_conditional", "First conditional", 7, "grammar"),
    ("second_conditional_intro", "Second conditional (intro)", 8, "grammar"),
    ("passive_present_basic", "Present passive (basic)", 7, "grammar"),
    ("used_to", "Used to", 6, "grammar"),
    ("gerunds_infinitives_basic", "Gerunds & infinitives (basic)", 6, "grammar"),
    ("relative_clauses_who_which", "Relative clauses who/which", 8, "grammar"),
    ("reported_speech_basic", "Reported speech (basic)", 9, "grammar"),
    ("adverbs_frequency_manner", "Adverbs of frequency & manner", 2, "grammar"),
    ("connectors_because_so", "Connectors because/so/but", 2, "grammar"),
    ("vocab_travel_daily", "Vocab: travel & daily routines", 4, "vocabulary"),
    ("vocab_opinions_feelings", "Vocab: opinions & feelings", 5, "vocabulary"),
]

A1_EDGES: list[tuple[str, str]] = [
    ("be_present", "possessives"),
    ("be_present", "there_is_are"),
    ("be_present", "past_simple_be"),
    ("subject_pronouns", "present_simple"),
    ("articles_a_an_the", "countable_uncountable_basic"),
    ("present_simple", "present_continuous"),
    ("present_simple", "can_cant"),
    ("present_simple", "wh_questions_basic"),
    ("present_simple", "past_simple_regular"),
    ("past_simple_be", "past_simple_regular"),
    ("past_simple_regular", "past_simple_irregular_common"),
    ("present_simple", "going_to_future"),
    ("countable_uncountable_basic", "some_any"),
]

A2_EDGES: list[tuple[str, str]] = [
    ("present_simple_vs_continuous", "past_continuous"),
    ("past_continuous", "past_simple_vs_continuous"),
    ("present_perfect_basic", "present_perfect_vs_past"),
    ("will_future", "going_to_vs_will"),
    ("modals_should_must", "modals_have_to"),
    ("first_conditional", "second_conditional_intro"),
    ("connectors_because_so", "relative_clauses_who_which"),
    ("present_perfect_basic", "used_to"),
]


def catalog_slug_set(level: CEFRLevel) -> set[str]:
    rows = A1_SKILLS if level == CEFRLevel.A1 else A2_SKILLS if level == CEFRLevel.A2 else []
    return {slug for slug, *_ in rows}


def _skill_rows(level: CEFRLevel, skills: list[tuple[str, str, int, str]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for slug, title, difficulty, skill_type in skills:
        rows.append(
            {
                "slug": slug,
                "title": title,
                "cefr_level": level,
                "skill_type": SkillTypeEnum(skill_type),
                "difficulty_in_level": difficulty,
                "is_active": True,
                "origin": "catalog",
            }
        )
    return rows


async def _upsert_skills(db: AsyncSession, rows: list[dict[str, Any]]) -> None:
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


async def _slug_to_id_map(db: AsyncSession, level: CEFRLevel) -> dict[str, int]:
    rows = (
        await db.execute(
            select(LearningSkillDB).where(
                LearningSkillDB.cefr_level == level,
                LearningSkillDB.origin == "catalog",
            )
        )
    ).scalars().all()
    return {s.slug: int(s.id) for s in rows}


async def _upsert_edges(
    db: AsyncSession, level: CEFRLevel, edges: list[tuple[str, str]]
) -> int:
    slug_to_id = await _slug_to_id_map(db, level)
    added = 0
    for frm_slug, to_slug in edges:
        frm_id = slug_to_id.get(frm_slug)
        to_id = slug_to_id.get(to_slug)
        if frm_id is None or to_id is None or frm_id == to_id:
            continue
        stmt = pg_insert(SkillEdgeDB).values(
            from_skill_id=frm_id,
            to_skill_id=to_id,
            relation="prerequisite",
        )
        stmt = stmt.on_conflict_do_nothing(constraint="uq_skill_edge")
        result = await db.execute(stmt)
        if result.rowcount:
            added += 1
    return added


async def _deactivate_legacy(db: AsyncSession) -> None:
    await db.execute(
        update(LearningSkillDB)
        .where(
            LearningSkillDB.cefr_level.in_([CEFRLevel.A1, CEFRLevel.A2]),
            LearningSkillDB.origin != "catalog",
        )
        .values(is_active=False)
    )


async def seed_cefr_ladder(db: AsyncSession) -> dict[str, int]:
    """Upsert A1+A2 catalog skills + edges; deactivate non-catalog A1/A2 skills."""
    await _upsert_skills(db, _skill_rows(CEFRLevel.A1, A1_SKILLS))
    await _upsert_skills(db, _skill_rows(CEFRLevel.A2, A2_SKILLS))
    await db.flush()
    edges_a1 = await _upsert_edges(db, CEFRLevel.A1, A1_EDGES)
    edges_a2 = await _upsert_edges(db, CEFRLevel.A2, A2_EDGES)
    await _deactivate_legacy(db)
    await db.flush()
    return {
        "a1": len(A1_SKILLS),
        "a2": len(A2_SKILLS),
        "edges": edges_a1 + edges_a2,
    }


async def _main() -> None:
    async with AsyncSessionLocal() as session:
        counts = await seed_cefr_ladder(session)
        await session.commit()
    print(
        f"Seeded CEFR ladder: A1={counts['a1']} A2={counts['a2']} "
        f"new_edges≈{counts['edges']}"
    )


if __name__ == "__main__":
    asyncio.run(_main())
