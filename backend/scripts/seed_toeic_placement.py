"""Seed a published TOEIC R+W pool with realistic practice content (local/dev).

Usage:
  PYTHONPATH=. .venv/bin/python -m scripts.seed_toeic_placement
  PYTHONPATH=. .venv/bin/python -m scripts.seed_toeic_placement --force
"""

from __future__ import annotations

import asyncio
import sys

from sqlalchemy import delete, select

from app.core.database import AsyncSessionLocal
from app.models.book import BookDB
from app.models.book_structure_preview import BookStructurePreviewDB
from app.models.enums import (
    QuizQuestionStatusEnum,
    QuizQuestionTypeEnum,
    ToeicPartEnum,
)
from app.models.learning_skill import LearningSkillDB
from app.models.quiz_passage import QuizPassageDB
from app.models.quiz_question import QuizQuestionDB
from app.services.placement.quotas import READING_QUOTA, WRITING_QUOTA

# Realistic Part 5 stems (cycle through for quota) — blank as ------- like official RC.
_R5_BANK: list[tuple[str, list[str], str]] = [
    (
        "The marketing team ------- the campaign results before Friday.",
        ["will review", "reviewing", "have review", "to review"],
        "will review",
    ),
    (
        "Please submit your expense report ------- the end of the month.",
        ["by", "until", "during", "since"],
        "by",
    ),
    (
        "Ms. Chen is responsible ------- coordinating the vendor contracts.",
        ["for", "to", "of", "with"],
        "for",
    ),
    (
        "The new software is ------- more efficient than the previous version.",
        ["considerably", "considerable", "consider", "considered"],
        "considerably",
    ),
    (
        "Neither the manager nor the assistants ------- available this afternoon.",
        ["are", "is", "be", "been"],
        "are",
    ),
    (
        "Customers who purchase online will receive a discount ------- shipping.",
        ["on", "at", "for", "to"],
        "on",
    ),
    (
        "The conference room has been reserved ------- 2 p.m. to 4 p.m.",
        ["from", "since", "until", "by"],
        "from",
    ),
    (
        "If the shipment ------- delayed, please notify the warehouse supervisor.",
        ["is", "will", "be", "were being"],
        "is",
    ),
    (
        "Dr. Patel asked that the laboratory ------- locked after hours.",
        ["be", "is", "being", "was"],
        "be",
    ),
    (
        "The brochure explains the benefits of the membership ------- detail.",
        ["in", "on", "at", "for"],
        "in",
    ),
]

_R6_SETS: list[dict] = [
    {
        "body": (
            "MEMO\nTo: All Staff\nFrom: Facilities\nRe: Parking garage repairs\n\n"
            "Beginning Monday, the south entrance of the parking garage will be closed "
            "for resurfacing. Employees should use the north entrance and allow extra "
            "time. The work is expected to last ------- (1) two weeks. Shuttle service "
            "from the overflow lot will run every ------- (2) minutes during peak hours. "
            "------- (3) ------- (4) Questions may be directed to facilities@example.com."
        ),
        "items": [
            (
                "Choose the best answer for blank (1).",
                ["approximately", "approximate", "approximation", "approximating"],
                "approximately",
            ),
            (
                "Choose the best answer for blank (2).",
                ["fifteen", "fifteenth", "fifteens", "fifteenthly"],
                "fifteen",
            ),
            (
                "Choose the best answer for blank (3).",
                [
                    "Please park only in marked spaces.",
                    "Overtime pay will increase next month.",
                    "The cafeteria menu changes daily.",
                    "New ID badges are required for visitors.",
                ],
                "Please park only in marked spaces.",
            ),
            (
                "Choose the best answer for blank (4).",
                ["Additionally", "However", "Instead", "Otherwise"],
                "Additionally",
            ),
        ],
    },
    {
        "body": (
            "Dear Ms. Alvarez,\n\nThank you for your interest in the customer-support role. "
            "We were impressed with your experience in retail and would like to invite you "
            "to a second interview next Thursday at 10:00 a.m. Please bring a list of "
            "professional references. ------- (1) If this time is inconvenient, let us know "
            "so we can ------- (2) another appointment. We look forward to ------- (3) with you. "
            "------- (4)\n\n"
            "Sincerely,\nJordan Lee\nHiring Coordinator"
        ),
        "items": [
            (
                "Choose the best answer for blank (1).",
                [
                    "We will also ask you to complete a short skills questionnaire.",
                    "The parking garage is closed on weekends.",
                    "Our office sells office supplies.",
                    "Please ignore previous messages.",
                ],
                "We will also ask you to complete a short skills questionnaire.",
            ),
            (
                "Choose the best answer for blank (2).",
                ["arrange", "arranging", "arrangement", "arranges"],
                "arrange",
            ),
            (
                "Choose the best answer for blank (3).",
                ["speaking", "speak", "spoken", "spoke"],
                "speaking",
            ),
            (
                "Choose the best answer for blank (4).",
                [
                    "Thank you again for considering this opportunity.",
                    "Please cancel your application immediately.",
                    "Ship the package by Friday.",
                    "The store opens at noon.",
                ],
                "Thank you again for considering this opportunity.",
            ),
        ],
    },
]

_R7_SETS: list[dict] = [
    {
        "body": (
            "City Transit Report — March\n\nRidership on the Blue Line increased by 12% "
            "compared with February, largely because of a new university semester and "
            "milder weather. On-time performance improved to 94% after signal upgrades "
            "near Central Station. However, evening crowding on trains departing between "
            "5:30 and 6:30 p.m. remains a concern. Transit officials plan to add two "
            "extra cars on weekdays starting April 1."
        ),
        "items": [
            (
                "What happened to Blue Line ridership in March?",
                ["It rose by 12%", "It fell by 12%", "It stayed the same", "It was not measured"],
                "It rose by 12%",
            ),
            (
                "What was the on-time rate after upgrades?",
                ["94%", "12%", "5:30%", "April 1%"],
                "94%",
            ),
            (
                "What problem still worries officials?",
                [
                    "Evening crowding on trains",
                    "Closed university campuses",
                    "Lack of mild weather",
                    "Too many extra cars",
                ],
                "Evening crowding on trains",
            ),
        ],
    },
    {
        "body": (
            "Product Notice — Apex Wireless Headphones\n\nApex has released firmware 2.4 "
            "to improve battery life and reduce audio lag during video calls. Users can "
            "update through the Apex Connect app. The update takes about eight minutes "
            "and requires the headphones to remain charged above 40%. Customers who "
            "purchased the product before January 2025 are eligible for a free carrying "
            "case by registering online before May 31."
        ),
        "items": [
            (
                "What does firmware 2.4 improve?",
                [
                    "Battery life and video-call audio lag",
                    "Shipping speed only",
                    "Store hours",
                    "Warranty length exclusively",
                ],
                "Battery life and video-call audio lag",
            ),
            (
                "How long does the update take?",
                ["About eight minutes", "Forty minutes", "One day", "May 31"],
                "About eight minutes",
            ),
            (
                "Who can get a free carrying case?",
                [
                    "Buyers before January 2025 who register by May 31",
                    "Any visitor to the store",
                    "Only employees",
                    "People without the app",
                ],
                "Buyers before January 2025 who register by May 31",
            ),
        ],
    },
]

_W1_PROMPTS: list[list[str]] = [
    ["laptop", "desk"],
    ["customer", "counter"],
    ["presentation", "screen"],
    ["warehouse", "boxes"],
    ["airport", "suitcase"],
]

_W2_EMAILS: list[dict] = [
    {
        "body": (
            "From: William Murphy\nTo: Mary Johnson\nSubject: Harper Business Magazine\n\n"
            "Dear Ms. Johnson,\nI am writing an article about business owners in your city "
            "and would like to interview you next week. Would you mind meeting sometime?\n\n"
            "Thank you,\nWilliam Murphy"
        ),
        "stem": (
            "Respond as Mary Johnson. Ask TWO questions and provide ONE time you can meet."
        ),
        "brief": {"must_ask": 2, "must_provide": 1, "role": "Mary Johnson"},
    },
    {
        "body": (
            "From: Amada Tipton\nTo: Human Resources\nSubject: Positions available\n\n"
            "Dear Sir or Madam,\nI recently graduated and am interested in Marketing "
            "opportunities. Could you advise on open roles and the application process?\n\n"
            "Thank you,\nAmada Tipton"
        ),
        "stem": (
            "Respond as an HR officer. Provide TWO pieces of information and ask ONE question."
        ),
        "brief": {"must_ask": 1, "must_provide": 2, "role": "HR officer"},
    },
]


async def _resolve_fks(db):
    skill = (await db.execute(select(LearningSkillDB).limit(1))).scalar_one_or_none()
    book = (await db.execute(select(BookDB).limit(1))).scalar_one_or_none()
    unit = (
        await db.execute(select(BookStructurePreviewDB).limit(1))
    ).scalar_one_or_none()
    if not skill or not book or not unit:
        raise SystemExit(
            "Need at least one learning_skill, book, and book_structure_preview row."
        )
    return int(skill.id), int(book.id), int(unit.id)


async def _clear_toeic_pool(db) -> None:
    await db.execute(
        delete(QuizQuestionDB).where(QuizQuestionDB.toeic_part.is_not(None))
    )
    await db.execute(delete(QuizPassageDB))
    await db.commit()


def _take_r5(n: int) -> list[tuple[str, list[str], str]]:
    out: list[tuple[str, list[str], str]] = []
    i = 0
    while len(out) < n:
        stem, opts, ans = _R5_BANK[i % len(_R5_BANK)]
        # Vary stems slightly so IDs/content aren't identical clones
        suffix = f" (set {i // len(_R5_BANK) + 1})" if i >= len(_R5_BANK) else ""
        out.append((stem.replace("____", "____") + suffix, opts, ans))
        i += 1
    return out


async def seed(*, force: bool = False) -> None:
    async with AsyncSessionLocal() as db:
        skill_id, book_id, unit_id = await _resolve_fks(db)
        existing = (
            await db.execute(
                select(QuizQuestionDB.id)
                .where(
                    QuizQuestionDB.toeic_part.is_not(None),
                    QuizQuestionDB.status == QuizQuestionStatusEnum.published,
                )
                .limit(1)
            )
        ).scalar_one_or_none()
        if existing is not None and not force:
            print("Published TOEIC items already exist; pass --force to replace.")
            return
        if force and existing is not None:
            await _clear_toeic_pool(db)

        for stem, opts, ans in _take_r5(READING_QUOTA["r5"]):
            db.add(
                QuizQuestionDB(
                    skill_id=skill_id,
                    book_id=book_id,
                    unit_id=unit_id,
                    question_type=QuizQuestionTypeEnum.mcq,
                    toeic_part=ToeicPartEnum.r5,
                    stem=stem,
                    options=opts,
                    answer=ans,
                    status=QuizQuestionStatusEnum.published,
                    difficulty="medium",
                )
            )

        r6_need = READING_QUOTA["r6"]
        r6_made = 0
        set_i = 0
        while r6_made < r6_need:
            spec = _R6_SETS[set_i % len(_R6_SETS)]
            set_i += 1
            passage = QuizPassageDB(
                book_id=book_id,
                unit_id=unit_id,
                toeic_part=ToeicPartEnum.r6,
                body=spec["body"] + (f"\n\n[Variant {set_i}]" if set_i > len(_R6_SETS) else ""),
                status=QuizQuestionStatusEnum.published,
            )
            db.add(passage)
            await db.flush()
            for stem, opts, ans in spec["items"]:
                if r6_made >= r6_need:
                    break
                db.add(
                    QuizQuestionDB(
                        skill_id=skill_id,
                        book_id=book_id,
                        unit_id=unit_id,
                        question_type=QuizQuestionTypeEnum.mcq,
                        toeic_part=ToeicPartEnum.r6,
                        passage_id=int(passage.id),
                        passage=passage.body,
                        stem=stem,
                        options=opts,
                        answer=ans,
                        status=QuizQuestionStatusEnum.published,
                        difficulty="medium",
                    )
                )
                r6_made += 1

        r7_need = READING_QUOTA["r7"]
        r7_made = 0
        set_i = 0
        while r7_made < r7_need:
            spec = _R7_SETS[set_i % len(_R7_SETS)]
            set_i += 1
            passage = QuizPassageDB(
                book_id=book_id,
                unit_id=unit_id,
                toeic_part=ToeicPartEnum.r7,
                body=spec["body"] + (f"\n\n[Variant {set_i}]" if set_i > len(_R7_SETS) else ""),
                status=QuizQuestionStatusEnum.published,
            )
            db.add(passage)
            await db.flush()
            for stem, opts, ans in spec["items"]:
                if r7_made >= r7_need:
                    break
                db.add(
                    QuizQuestionDB(
                        skill_id=skill_id,
                        book_id=book_id,
                        unit_id=unit_id,
                        question_type=QuizQuestionTypeEnum.mcq,
                        toeic_part=ToeicPartEnum.r7,
                        passage_id=int(passage.id),
                        passage=passage.body,
                        stem=stem,
                        options=opts,
                        answer=ans,
                        status=QuizQuestionStatusEnum.published,
                        difficulty="medium",
                    )
                )
                r7_made += 1

        for words in _W1_PROMPTS[: WRITING_QUOTA["w1"]]:
            db.add(
                QuizQuestionDB(
                    skill_id=skill_id,
                    book_id=book_id,
                    unit_id=unit_id,
                    question_type=QuizQuestionTypeEnum.writing,
                    toeic_part=ToeicPartEnum.w1,
                    stem=(
                        "Write one sentence using the two words below "
                        "(any order; you may change word forms)."
                    ),
                    prompt_words=words,
                    media_url=None,
                    answer="",
                    status=QuizQuestionStatusEnum.published,
                    difficulty="medium",
                )
            )

        for spec in _W2_EMAILS[: WRITING_QUOTA["w2"]]:
            passage = QuizPassageDB(
                book_id=book_id,
                unit_id=unit_id,
                toeic_part=ToeicPartEnum.w2,
                body=spec["body"],
                status=QuizQuestionStatusEnum.published,
            )
            db.add(passage)
            await db.flush()
            db.add(
                QuizQuestionDB(
                    skill_id=skill_id,
                    book_id=book_id,
                    unit_id=unit_id,
                    question_type=QuizQuestionTypeEnum.writing,
                    toeic_part=ToeicPartEnum.w2,
                    passage_id=int(passage.id),
                    passage=passage.body,
                    stem=spec["stem"],
                    task_brief=spec["brief"],
                    answer="",
                    status=QuizQuestionStatusEnum.published,
                    difficulty="medium",
                )
            )

        db.add(
            QuizQuestionDB(
                skill_id=skill_id,
                book_id=book_id,
                unit_id=unit_id,
                question_type=QuizQuestionTypeEnum.writing,
                toeic_part=ToeicPartEnum.w3,
                stem=(
                    "Thanks to modern technology, more people can work from home. "
                    "What are the advantages and disadvantages of working at home? "
                    "Support your answer with specific reasons and examples."
                ),
                task_brief={"min_words": 300},
                answer="",
                status=QuizQuestionStatusEnum.published,
                difficulty="medium",
            )
        )
        await db.commit()
        print("Seeded realistic TOEIC R+W placement pool.")


if __name__ == "__main__":
    force = "--force" in sys.argv
    asyncio.run(seed(force=force))
    sys.exit(0)
