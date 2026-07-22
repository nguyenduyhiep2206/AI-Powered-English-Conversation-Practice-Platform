"""Idempotent seed for baseline chat scenarios.

The roadmap assembler attaches one active scenario per week, preferring a
category derived from the user's goal (see ``GOAL_TO_CATEGORY``) and falling
back to any active scenario at the level. Without at least one active scenario
per CEFR level, ``assemble_user_roadmap`` raises "No scenarios yet".

This seed inserts, for every CEFR level, one scenario for each category the
roadmap maps goals onto (small talk, job interview, travel, custom), so any
learner goal resolves to a category match. Re-running upserts by ``slug``.

Run:
    python -m app.seeds.scenarios
"""

from __future__ import annotations

import asyncio
from typing import Any

from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.core.database import AsyncSessionLocal
from app.models.enums import CEFRLevel, ScenarioCategoryEnum
from app.models.scenario import ScenarioDB

# Level-tuned goal prompts keep the same scenario category meaningful as the
# learner advances (simpler exchanges at A1, nuanced/idiomatic ones at C1).
_LEVEL_TONE: dict[CEFRLevel, str] = {
    CEFRLevel.A1: "Use short, simple sentences and everyday words.",
    CEFRLevel.A2: "Use simple connected sentences and common phrases.",
    CEFRLevel.B1: "Handle the exchange with clear, connected explanations.",
    CEFRLevel.B2: "Speak fluently with detail, opinions, and follow-up questions.",
    CEFRLevel.C1: "Use precise, idiomatic language and handle nuance smoothly.",
}

# (category, title, ai_role, user_role, goal, vocab)
_TEMPLATES: list[tuple[ScenarioCategoryEnum, str, str, str, str, list[str]]] = [
    (
        ScenarioCategoryEnum.small_talk,
        "Meeting a new neighbour",
        "A friendly neighbour who just moved in next door",
        "A resident welcoming the newcomer",
        "Introduce yourself, ask where they moved from, and offer help settling in.",
        ["neighbour", "move in", "settle in", "How's it going?", "let me know"],
    ),
    (
        ScenarioCategoryEnum.job_interview,
        "First-round job interview",
        "A hiring manager interviewing for an entry-level role",
        "A candidate applying for the job",
        "Introduce your background, describe a strength, and ask one question about the role.",
        ["experience", "strength", "responsibility", "team", "Could you tell me..."],
    ),
    (
        ScenarioCategoryEnum.travel,
        "Checking in at a hotel",
        "A hotel receptionist at the front desk",
        "A traveller arriving to check in",
        "Give your reservation name, confirm the room, and ask about breakfast and wifi.",
        ["reservation", "check in", "key card", "breakfast", "What time is..."],
    ),
    (
        ScenarioCategoryEnum.custom,
        "Daily life role-play",
        "A helpful conversation partner adapting to the topic",
        "A learner practising a real-life situation",
        "Pick a familiar daily situation and keep a natural back-and-forth going.",
        ["actually", "by the way", "I mean", "sort of", "let me think"],
    ),
]


def _build_rows() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for level in CEFRLevel:
        tone = _LEVEL_TONE[level]
        for order_index, (category, title, ai_role, user_role, goal, vocab) in enumerate(
            _TEMPLATES
        ):
            level_code = level.value.lower()
            rows.append(
                {
                    "title": f"{title} ({level.value})",
                    "slug": f"{category.value}-{level_code}",
                    "description": f"{title} — {level.value} speaking practice.",
                    "category": category,
                    "level": level,
                    "ai_role": ai_role,
                    "user_role": user_role,
                    "goal_prompt": f"{goal} {tone}",
                    "suggested_vocab": vocab,
                    "order_index": order_index,
                    "is_active": True,
                }
            )
    return rows


async def seed_scenarios() -> int:
    rows = _build_rows()
    async with AsyncSessionLocal() as session:
        for row in rows:
            stmt = pg_insert(ScenarioDB).values(**row)
            stmt = stmt.on_conflict_do_update(
                index_elements=[ScenarioDB.slug],
                set_={
                    "title": stmt.excluded.title,
                    "description": stmt.excluded.description,
                    "category": stmt.excluded.category,
                    "level": stmt.excluded.level,
                    "ai_role": stmt.excluded.ai_role,
                    "user_role": stmt.excluded.user_role,
                    "goal_prompt": stmt.excluded.goal_prompt,
                    "suggested_vocab": stmt.excluded.suggested_vocab,
                    "order_index": stmt.excluded.order_index,
                    "is_active": stmt.excluded.is_active,
                },
            )
            await session.execute(stmt)
        await session.commit()
    return len(rows)


async def _main() -> None:
    count = await seed_scenarios()
    print(f"Seeded/updated {count} scenarios across {len(list(CEFRLevel))} CEFR levels.")


if __name__ == "__main__":
    asyncio.run(_main())
