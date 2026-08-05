"""Idempotent seed for Theme Units over CEFR A1+A2 catalog skills.

Run:
    python -m app.seeds.theme_units_a1_a2
"""

from __future__ import annotations

import asyncio
from typing import Any

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import AsyncSessionLocal
from app.models.enums import CEFRLevel
from app.models.learning_skill import LearningSkillDB
from app.models.theme_unit import LearningThemeUnitDB, ThemeUnitSkillDB
from app.seeds.cefr_ladder_a1_a2 import A1_SKILLS, A2_SKILLS

# (slug, title, can_do, skill_slugs)
A1_UNITS: list[tuple[str, str, str, list[str]]] = [
    (
        "a1_be_and_people",
        "Be, people & basics",
        "I can introduce myself and talk about people using be and pronouns.",
        [
            "be_present",
            "subject_pronouns",
            "articles_a_an_the",
            "this_that_these_those",
            "possessives",
            "everyday_vocab_people",
        ],
    ),
    (
        "a1_have_and_places",
        "Have got, there is & places",
        "I can describe what I have and where things are.",
        [
            "have_got",
            "there_is_are",
            "prepositions_place",
            "everyday_vocab_places",
        ],
    ),
    (
        "a1_present_routines",
        "Present routines & ability",
        "I can talk about habits, what is happening now, and what I can do.",
        [
            "present_simple",
            "present_continuous",
            "can_cant",
            "imperatives",
            "wh_questions_basic",
            "prepositions_time_basic",
        ],
    ),
    (
        "a1_quantity",
        "Quantity basics",
        "I can talk about amounts with countable and uncountable nouns.",
        [
            "countable_uncountable_basic",
            "some_any",
        ],
    ),
    (
        "a1_past_and_plans",
        "Past events & future plans",
        "I can talk about the past and plans with going to.",
        [
            "past_simple_be",
            "past_simple_regular",
            "past_simple_irregular_common",
            "going_to_future",
        ],
    ),
]

A2_UNITS: list[tuple[str, str, str, list[str]]] = [
    (
        "a2_building_blocks",
        "Building blocks & connectors",
        "I can link ideas and add detail with adverbs and connectors.",
        [
            "adverbs_frequency_manner",
            "connectors_because_so",
            "quantifiers_much_many",
        ],
    ),
    (
        "a2_now_vs_ongoing",
        "Talking about now vs ongoing",
        "I can choose present simple or continuous appropriately.",
        ["present_simple_vs_continuous"],
    ),
    (
        "a2_talk_about_past",
        "Talking about the past",
        "I can talk about past events using past simple and past continuous.",
        [
            "past_continuous",
            "past_simple_vs_continuous",
            "used_to",
        ],
    ),
    (
        "a2_experience",
        "Experience & recent past",
        "I can talk about experience and recent events with present perfect.",
        [
            "present_perfect_basic",
            "present_perfect_vs_past",
        ],
    ),
    (
        "a2_future",
        "Future plans & predictions",
        "I can talk about the future with will and going to.",
        [
            "will_future",
            "going_to_vs_will",
        ],
    ),
    (
        "a2_advice",
        "Advice & obligation",
        "I can give advice and talk about rules with modals.",
        [
            "modals_should_must",
            "modals_have_to",
        ],
    ),
    (
        "a2_describe_compare",
        "Describing & comparing",
        "I can compare things and use basic passives and conditionals.",
        [
            "comparatives_superlatives",
            "passive_present_basic",
            "first_conditional",
            "second_conditional_intro",
            "gerunds_infinitives_basic",
        ],
    ),
    (
        "a2_opinions_travel",
        "Opinions, clauses & travel",
        "I can share opinions, add relative clauses, and use travel vocabulary.",
        [
            "relative_clauses_who_which",
            "reported_speech_basic",
            "vocab_travel_daily",
            "vocab_opinions_feelings",
        ],
    ),
]


def all_unit_skill_slugs(
    units: list[tuple[str, str, str, list[str]]],
) -> set[str]:
    out: set[str] = set()
    for _, _, _, skills in units:
        out.update(skills)
    return out


async def seed_theme_units(session: AsyncSession) -> dict[str, Any]:
    catalog_rows = list(
        (
            await session.execute(
                select(LearningSkillDB).where(
                    LearningSkillDB.origin == "catalog",
                    LearningSkillDB.is_active.is_(True),
                )
            )
        )
        .scalars()
        .all()
    )
    skill_id_by_key: dict[tuple[str, str], int] = {}
    for row in catalog_rows:
        level = (
            row.cefr_level.value
            if hasattr(row.cefr_level, "value")
            else str(row.cefr_level)
        )
        skill_id_by_key[(str(row.slug), level)] = int(row.id)

    unit_specs = [
        (CEFRLevel.A1, A1_UNITS),
        (CEFRLevel.A2, A2_UNITS),
    ]
    units_upserted = 0
    links_upserted = 0

    for level, units in unit_specs:
        level_s = level.value
        for sort_order, (slug, title, can_do, skill_slugs) in enumerate(units):
            stmt = (
                pg_insert(LearningThemeUnitDB)
                .values(
                    slug=slug,
                    cefr_level=level,
                    title=title,
                    can_do=can_do,
                    sort_order=sort_order,
                    is_active=True,
                )
                .on_conflict_do_update(
                    constraint="uq_theme_units_slug_level",
                    set_={
                        "title": title,
                        "can_do": can_do,
                        "sort_order": sort_order,
                        "is_active": True,
                    },
                )
                .returning(LearningThemeUnitDB.id)
            )
            unit_id = int((await session.execute(stmt)).scalar_one())
            units_upserted += 1

            for position, skill_slug in enumerate(skill_slugs):
                skill_id = skill_id_by_key.get((skill_slug, level_s))
                if skill_id is None:
                    raise ValueError(
                        f"Theme unit {slug}: missing catalog skill "
                        f"{skill_slug!r} @ {level_s}"
                    )
                link = (
                    pg_insert(ThemeUnitSkillDB)
                    .values(
                        theme_unit_id=unit_id,
                        skill_id=skill_id,
                        position=position,
                    )
                    .on_conflict_do_update(
                        constraint="uq_theme_unit_skills_skill_id",
                        set_={
                            "theme_unit_id": unit_id,
                            "position": position,
                        },
                    )
                )
                await session.execute(link)
                links_upserted += 1

    await session.commit()
    return {
        "units": units_upserted,
        "links": links_upserted,
        "a1_skills_covered": len(all_unit_skill_slugs(A1_UNITS)),
        "a2_skills_covered": len(all_unit_skill_slugs(A2_UNITS)),
        "a1_catalog": len(A1_SKILLS),
        "a2_catalog": len(A2_SKILLS),
    }


async def main() -> None:
    async with AsyncSessionLocal() as session:
        summary = await seed_theme_units(session)
        print(summary)


if __name__ == "__main__":
    asyncio.run(main())
