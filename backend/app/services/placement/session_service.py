"""TOEIC Reading + Writing placement sessions (timed form)."""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta, timezone
from random import Random
from typing import Any

from sqlalchemy.orm.attributes import flag_modified
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import CEFRLevel, PlacementAttemptStatusEnum, QuizQuestionStatusEnum
from app.models.placement_attempt import PlacementAttemptAnswerDB, PlacementAttemptDB
from app.models.profile import UserProfileDB
from app.models.quiz_passage import QuizPassageDB
from app.models.quiz_question import QuizQuestionDB
from app.services.mastery_service import apply_answer
from app.services.placement.assembler import BankTooSmallError, assemble_form
from app.services.placement.bank import grade_placement_answer
from app.services.placement.quotas import READING_MINUTES, WRITING_MINUTES
from app.services.placement.score_map import (
    blend_to_cefr,
    placement_sublevel,
    reading_scale,
    writing_scale,
)
from app.services.placement.writing_grader import grade_writing_task
from app.services.roadmap_assembler_service import clear_user_roadmap

RETAKE_COOLDOWN_DAYS = 7
INSUFFICIENT_BANK_MSG = "Placement bank not ready: not enough published TOEIC items."
# Back-compat alias for API mapping
INSUFFICIENT_ADAPTIVE_BANK_MSG = INSUFFICIENT_BANK_MSG


def retake_allowed(
    last_completed_at: datetime | None,
    now: datetime | None = None,
) -> bool:
    if last_completed_at is None:
        return True
    current = now or datetime.now(timezone.utc)
    completed = last_completed_at
    if completed.tzinfo is None:
        completed = completed.replace(tzinfo=timezone.utc)
    return current - completed >= timedelta(days=RETAKE_COOLDOWN_DAYS)


def _retry_after_at(last_completed_at: datetime) -> datetime:
    completed = last_completed_at
    if completed.tzinfo is None:
        completed = completed.replace(tzinfo=timezone.utc)
    return completed + timedelta(days=RETAKE_COOLDOWN_DAYS)


async def _get_profile(db: AsyncSession, user_id: int) -> UserProfileDB | None:
    return (
        await db.execute(select(UserProfileDB).where(UserProfileDB.user_id == user_id))
    ).scalar_one_or_none()


async def _require_survey_done(db: AsyncSession, user_id: int) -> UserProfileDB:
    profile = await _get_profile(db, user_id)
    if profile is None or not profile.survey_done:
        raise PermissionError("Hoàn thành survey trước khi làm placement")
    return profile


async def _get_in_progress(db: AsyncSession, user_id: int) -> PlacementAttemptDB | None:
    return (
        await db.execute(
            select(PlacementAttemptDB)
            .where(
                PlacementAttemptDB.user_id == user_id,
                PlacementAttemptDB.status == PlacementAttemptStatusEnum.in_progress,
            )
            .order_by(PlacementAttemptDB.started_at.desc(), PlacementAttemptDB.id.desc())
            .limit(1)
        )
    ).scalar_one_or_none()


async def _abandon_in_progress(
    db: AsyncSession, user_id: int, *, keep_id: int | None = None
) -> None:
    stmt = (
        update(PlacementAttemptDB)
        .where(
            PlacementAttemptDB.user_id == user_id,
            PlacementAttemptDB.status == PlacementAttemptStatusEnum.in_progress,
        )
        .values(status=PlacementAttemptStatusEnum.abandoned, current_question_id=None)
    )
    if keep_id is not None:
        stmt = stmt.where(PlacementAttemptDB.id != keep_id)
    await db.execute(stmt)


async def _last_completed_at(db: AsyncSession, user_id: int) -> datetime | None:
    return (
        await db.execute(
            select(PlacementAttemptDB.completed_at)
            .where(
                PlacementAttemptDB.user_id == user_id,
                PlacementAttemptDB.status == PlacementAttemptStatusEnum.completed,
            )
            .order_by(PlacementAttemptDB.completed_at.desc())
            .limit(1)
        )
    ).scalar_one_or_none()


def _retake_allowed_for_profile(
    *,
    has_in_progress: bool,
    last_completed_at: datetime | None,
    placement_score: int | None,
    now: datetime,
) -> bool:
    if has_in_progress:
        return False
    if placement_score is None:
        return True
    return retake_allowed(last_completed_at, now)


async def get_retake_status(db: AsyncSession, user_id: int) -> dict[str, Any]:
    profile = await _require_survey_done(db, user_id)
    in_progress = await _get_in_progress(db, user_id)
    last_done = await _last_completed_at(db, user_id)
    now = datetime.now(timezone.utc)
    allowed = _retake_allowed_for_profile(
        has_in_progress=in_progress is not None,
        last_completed_at=last_done,
        placement_score=profile.placement_score,
        now=now,
    )
    retry_after = (
        _retry_after_at(last_done)
        if (not allowed and in_progress is None and last_done is not None)
        else None
    )
    return {
        "allowed": allowed,
        "has_in_progress": in_progress is not None,
        "retry_after_at": retry_after,
    }


def _question_to_item(q: QuizQuestionDB) -> dict[str, Any]:
    part = q.toeic_part.value if q.toeic_part else None
    cefr = q.cefr_level.value if q.cefr_level else None
    qtype = q.question_type.value if hasattr(q.question_type, "value") else str(q.question_type)
    return {
        "id": int(q.id),
        "toeic_part": part,
        "stem": q.stem,
        "options": q.options,
        "answer": q.answer,
        "skill_id": int(q.skill_id) if q.skill_id else None,
        "cefr_level": cefr,
        "passage_id": int(q.passage_id) if q.passage_id else None,
        "prompt_words": q.prompt_words,
        "media_url": q.media_url,
        "task_brief": q.task_brief,
        "question_type": qtype,
        "passage": q.passage,
    }


async def _load_published_toeic_pool(
    db: AsyncSession,
) -> tuple[dict[str, list[dict[str, Any]]], dict[int, dict[str, Any]]]:
    rows = list(
        (
            await db.execute(
                select(QuizQuestionDB).where(
                    QuizQuestionDB.status == QuizQuestionStatusEnum.published,
                    QuizQuestionDB.toeic_part.is_not(None),
                )
            )
        )
        .scalars()
        .all()
    )
    by_part: dict[str, list[dict[str, Any]]] = defaultdict(list)
    passage_ids: set[int] = set()
    for q in rows:
        item = _question_to_item(q)
        if not item["toeic_part"]:
            continue
        by_part[item["toeic_part"]].append(item)
        if item["passage_id"]:
            passage_ids.add(item["passage_id"])

    passages: dict[int, dict[str, Any]] = {}
    if passage_ids:
        prow = (
            await db.execute(select(QuizPassageDB).where(QuizPassageDB.id.in_(passage_ids)))
        ).scalars().all()
        for p in prow:
            part = p.toeic_part.value if p.toeic_part else None
            passages[int(p.id)] = {
                "id": int(p.id),
                "body": p.body,
                "toeic_part": part,
                "media_url": p.media_url,
            }
    return by_part, passages


def _section_ends_at(minutes: int, now: datetime | None = None) -> datetime:
    current = now or datetime.now(timezone.utc)
    return current + timedelta(minutes=minutes)


def _collect_writing_feedback(snap: dict[str, Any]) -> list[dict[str, Any]]:
    raw = list(snap.get("_writing_feedback") or [])
    by_id: dict[int, dict[str, Any]] = {}
    for row in raw:
        try:
            iid = int(row.get("item_id"))
        except (TypeError, ValueError):
            continue
        by_id[iid] = row
    return list(by_id.values())


async def _load_saved_answers(db: AsyncSession, attempt_id: int) -> dict[str, str]:
    rows = (
        await db.execute(
            select(PlacementAttemptAnswerDB).where(
                PlacementAttemptAnswerDB.attempt_id == attempt_id
            )
        )
    ).scalars().all()
    return {str(int(r.question_id)): (r.given_answer or "") for r in rows}


async def _public_session(
    db: AsyncSession,
    attempt: PlacementAttemptDB,
    *,
    done: bool = False,
) -> dict[str, Any]:
    snap = attempt.form_snapshot or {}
    public_snap = {
        "reading_items": snap.get("reading_items") or [],
        "writing_items": snap.get("writing_items") or [],
        "passages": snap.get("passages") or {},
    }
    saved = await _load_saved_answers(db, int(attempt.id)) if attempt.id else {}
    return {
        "done": done,
        "attempt_id": int(attempt.id),
        "section": attempt.section,
        "section_ends_at": attempt.section_ends_at,
        "form": public_snap,
        "saved_answers": saved,
        "reading_raw": attempt.reading_raw,
        "reading_scale": attempt.reading_scale,
        "writing_raw": attempt.writing_raw,
        "writing_scale": attempt.writing_scale,
        "placement_score": attempt.result_sublevel,
        "current_level": (
            attempt.result_level.value
            if attempt.result_level and hasattr(attempt.result_level, "value")
            else attempt.result_level
        ),
        "writing_feedback": _collect_writing_feedback(snap),
        "onboarding_complete": done,
    }

async def _require_owner_attempt(
    db: AsyncSession, user_id: int, attempt_id: int
) -> PlacementAttemptDB:
    attempt = (
        await db.execute(
            select(PlacementAttemptDB).where(PlacementAttemptDB.id == attempt_id)
        )
    ).scalar_one_or_none()
    if attempt is None or int(attempt.user_id) != user_id:
        raise PermissionError("Placement attempt không hợp lệ")
    if attempt.status != PlacementAttemptStatusEnum.in_progress:
        raise RuntimeError("Placement attempt không còn in_progress")
    return attempt


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _timed_out(attempt: PlacementAttemptDB, now: datetime | None = None) -> bool:
    ends = attempt.section_ends_at
    if ends is None:
        return False
    current = now or _now()
    if ends.tzinfo is None:
        ends = ends.replace(tzinfo=timezone.utc)
    return current >= ends


def _form_is_usable(snap: Any) -> bool:
    """True when snapshot has a TOEIC reading form (not a legacy adaptive attempt)."""
    if not isinstance(snap, dict):
        return False
    reading = snap.get("reading_items") or []
    return isinstance(reading, list) and len(reading) > 0


async def start_or_resume_session(db: AsyncSession, user_id: int) -> dict[str, Any]:
    profile = await _require_survey_done(db, user_id)
    existing = await _get_in_progress(db, user_id)
    if existing is not None and _form_is_usable(existing.form_snapshot):
        await _abandon_in_progress(db, user_id, keep_id=int(existing.id))
        await db.commit()
        return await _public_session(db, existing)

    # Legacy adaptive / empty snapshots cannot serve TOEIC UI — abandon and rebuild.
    if existing is not None:
        await _abandon_in_progress(db, user_id, keep_id=None)
        await db.commit()

    now = _now()
    last_done = await _last_completed_at(db, user_id)
    if profile.placement_score is not None and not retake_allowed(last_done, now):
        raise RuntimeError("Chưa đến hạn làm lại placement")

    by_part, passages = await _load_published_toeic_pool(db)
    try:
        snapshot = assemble_form(by_part, passages, rng=Random())
    except BankTooSmallError as exc:
        raise ValueError(INSUFFICIENT_BANK_MSG) from exc

    attempt = PlacementAttemptDB(
        user_id=user_id,
        status=PlacementAttemptStatusEnum.in_progress,
        form_snapshot=snapshot,
        section="reading",
        section_ends_at=_section_ends_at(READING_MINUTES, now),
        questions_asked=0,
        seen_question_ids=[],
    )
    db.add(attempt)
    await db.commit()
    await db.refresh(attempt)
    return await _public_session(db, attempt)


async def get_current_session(db: AsyncSession, user_id: int) -> dict[str, Any] | None:
    await _require_survey_done(db, user_id)
    attempt = await _get_in_progress(db, user_id)
    if attempt is None:
        return None
    if not _form_is_usable(attempt.form_snapshot):
        # Force client to POST /sessions and rebuild a TOEIC form.
        return None
    return await _public_session(db, attempt)


async def submit_reading_answers(
    db: AsyncSession,
    user_id: int,
    attempt_id: int,
    answers: list[dict[str, Any]],
) -> dict[str, Any]:
    attempt = await _require_owner_attempt(db, user_id, attempt_id)
    if attempt.section != "reading":
        raise ValueError("Không còn ở section Reading")
    snap = dict(attempt.form_snapshot or {})
    answer_key = snap.get("_answers") or {}
    reading_ids = set(snap.get("_reading_ids") or [])
    items = snap.get("_items") or {}

    for row in answers:
        qid = int(row["item_id"])
        given = str(row.get("given_answer") or "")
        if qid not in reading_ids:
            raise ValueError(f"item_id {qid} không thuộc đề Reading")
        expected = str(answer_key.get(str(qid)) or "")
        correct = grade_placement_answer(expected, given)
        meta = items.get(str(qid)) or {}
        await _upsert_answer(
            db,
            attempt_id=int(attempt.id),
            question_id=qid,
            skill_id=meta.get("skill_id"),
            cefr_level=meta.get("cefr_level"),
            given_answer=given,
            is_correct=correct,
            score=1.0 if correct else 0.0,
        )

    await db.commit()
    await db.refresh(attempt)
    return await _public_session(db, attempt)


async def submit_writing_answer(
    db: AsyncSession,
    user_id: int,
    attempt_id: int,
    item_id: int,
    text: str,
) -> dict[str, Any]:
    attempt = await _require_owner_attempt(db, user_id, attempt_id)
    if attempt.section != "writing":
        raise ValueError("Chưa vào section Writing")
    snap = dict(attempt.form_snapshot or {})
    writing_ids = set(snap.get("_writing_ids") or [])
    if item_id not in writing_ids:
        raise ValueError(f"item_id {item_id} không thuộc đề Writing")
    meta = (snap.get("_items") or {}).get(str(item_id)) or {}
    part = str(meta.get("toeic_part") or "")
    graded = grade_writing_task(
        part=part,
        stem=str(meta.get("stem") or ""),
        task_brief=meta.get("task_brief"),
        prompt_words=meta.get("prompt_words"),
        media_url=meta.get("media_url"),
        text=text,
    )
    await _upsert_answer(
        db,
        attempt_id=int(attempt.id),
        question_id=item_id,
        skill_id=meta.get("skill_id"),
        cefr_level=meta.get("cefr_level"),
        given_answer=text,
        is_correct=None,
        score=float(graded["score"]),
        ai_scores=graded.get("ai_scores"),
        ai_feedback=graded.get("ai_feedback"),
    )
    feedback = list(snap.get("_writing_feedback") or [])
    entry = {
        "item_id": item_id,
        "score": graded["score"],
        "feedback": graded.get("ai_feedback"),
    }
    replaced = False
    for i, row in enumerate(feedback):
        if int(row.get("item_id") or -1) == item_id:
            feedback[i] = entry
            replaced = True
            break
    if not replaced:
        feedback.append(entry)
    snap["_writing_feedback"] = feedback
    attempt.form_snapshot = snap
    flag_modified(attempt, "form_snapshot")
    await db.commit()
    await db.refresh(attempt)
    return await _public_session(db, attempt)


async def advance_section(db: AsyncSession, user_id: int, attempt_id: int) -> dict[str, Any]:
    attempt = await _require_owner_attempt(db, user_id, attempt_id)
    if attempt.section != "reading":
        raise ValueError("Chỉ advance từ Reading sang Writing")
    snap = attempt.form_snapshot or {}
    reading_ids = list(snap.get("_reading_ids") or [])
    answered = await _answered_question_ids(db, int(attempt.id))
    if not _timed_out(attempt) and not set(reading_ids).issubset(answered):
        raise ValueError("Chưa trả lời hết Reading (hoặc chờ hết giờ)")

    await _fill_missing_reading_wrong(db, attempt, reading_ids, answered)
    correct = await _count_reading_correct(db, int(attempt.id))
    attempt.reading_raw = correct
    attempt.reading_scale = reading_scale(correct, total=len(reading_ids) or 100)
    attempt.section = "writing"
    attempt.section_ends_at = _section_ends_at(WRITING_MINUTES)
    await db.commit()
    await db.refresh(attempt)
    return await _public_session(db, attempt)


async def complete_session(db: AsyncSession, user_id: int, attempt_id: int) -> dict[str, Any]:
    attempt = await _require_owner_attempt(db, user_id, attempt_id)
    if attempt.section == "reading":
        raise ValueError("Hãy advance sang Writing trước khi complete")
    if attempt.section == "done":
        return await _public_session(db, attempt, done=True)

    snap = attempt.form_snapshot or {}
    writing_ids = list(snap.get("_writing_ids") or [])
    answered = await _answered_question_ids(db, int(attempt.id))
    if not _timed_out(attempt) and not set(writing_ids).issubset(answered):
        raise ValueError("Chưa nộp hết Writing (hoặc chờ hết giờ)")

    await _fill_missing_writing_zero(db, attempt, writing_ids, answered)
    raw = await _sum_writing_scores(db, int(attempt.id), writing_ids)
    attempt.writing_raw = raw
    attempt.writing_scale = writing_scale(raw)

    r_scale = int(attempt.reading_scale or reading_scale(int(attempt.reading_raw or 0)))
    w_scale = int(attempt.writing_scale or 0)
    cefr = blend_to_cefr(r_scale, w_scale)
    sub = placement_sublevel(r_scale, w_scale, cefr)
    attempt.result_level = CEFRLevel(cefr)
    attempt.result_sublevel = sub
    attempt.section = "done"
    attempt.status = PlacementAttemptStatusEnum.completed
    attempt.completed_at = _now()

    profile = await _require_survey_done(db, user_id)
    was_retake = profile.placement_score is not None
    profile.current_level = CEFRLevel(cefr)
    profile.placement_score = sub
    if was_retake:
        await clear_user_roadmap(db, user_id)

    await _seed_reading_mastery(db, user_id, int(attempt.id))
    await db.commit()
    await db.refresh(attempt)
    return await _public_session(db, attempt, done=True)


async def _upsert_answer(
    db: AsyncSession,
    *,
    attempt_id: int,
    question_id: int,
    skill_id: int | None,
    cefr_level: str | None,
    given_answer: str,
    is_correct: bool | None,
    score: float | None = None,
    ai_scores: dict | None = None,
    ai_feedback: str | None = None,
) -> None:
    existing = (
        await db.execute(
            select(PlacementAttemptAnswerDB).where(
                PlacementAttemptAnswerDB.attempt_id == attempt_id,
                PlacementAttemptAnswerDB.question_id == question_id,
            )
        )
    ).scalar_one_or_none()
    level = None
    if cefr_level:
        try:
            level = CEFRLevel(cefr_level)
        except ValueError:
            level = None
    if existing is None:
        db.add(
            PlacementAttemptAnswerDB(
                attempt_id=attempt_id,
                question_id=question_id,
                skill_id=skill_id,
                cefr_level=level,
                given_answer=given_answer,
                is_correct=is_correct,
                score=score,
                ai_scores=ai_scores,
                ai_feedback=ai_feedback,
            )
        )
    else:
        existing.given_answer = given_answer
        existing.is_correct = is_correct
        existing.score = score
        existing.ai_scores = ai_scores
        existing.ai_feedback = ai_feedback


async def _answered_question_ids(db: AsyncSession, attempt_id: int) -> set[int]:
    rows = (
        await db.execute(
            select(PlacementAttemptAnswerDB.question_id).where(
                PlacementAttemptAnswerDB.attempt_id == attempt_id
            )
        )
    ).scalars().all()
    return {int(x) for x in rows}


async def _fill_missing_reading_wrong(
    db: AsyncSession,
    attempt: PlacementAttemptDB,
    reading_ids: list[int],
    answered: set[int],
) -> None:
    snap = attempt.form_snapshot or {}
    items = snap.get("_items") or {}
    for qid in reading_ids:
        if qid in answered:
            continue
        meta = items.get(str(qid)) or {}
        await _upsert_answer(
            db,
            attempt_id=int(attempt.id),
            question_id=qid,
            skill_id=meta.get("skill_id"),
            cefr_level=meta.get("cefr_level"),
            given_answer="",
            is_correct=False,
            score=0.0,
        )


async def _fill_missing_writing_zero(
    db: AsyncSession,
    attempt: PlacementAttemptDB,
    writing_ids: list[int],
    answered: set[int],
) -> None:
    snap = attempt.form_snapshot or {}
    items = snap.get("_items") or {}
    for qid in writing_ids:
        if qid in answered:
            continue
        meta = items.get(str(qid)) or {}
        await _upsert_answer(
            db,
            attempt_id=int(attempt.id),
            question_id=qid,
            skill_id=meta.get("skill_id"),
            cefr_level=meta.get("cefr_level"),
            given_answer="",
            is_correct=None,
            score=0.0,
            ai_feedback="No response submitted.",
        )


async def _count_reading_correct(db: AsyncSession, attempt_id: int) -> int:
    rows = (
        await db.execute(
            select(PlacementAttemptAnswerDB).where(
                PlacementAttemptAnswerDB.attempt_id == attempt_id,
                PlacementAttemptAnswerDB.is_correct.is_(True),
            )
        )
    ).scalars().all()
    return len(list(rows))


async def _sum_writing_scores(
    db: AsyncSession, attempt_id: int, writing_ids: list[int]
) -> float:
    if not writing_ids:
        return 0.0
    rows = (
        await db.execute(
            select(PlacementAttemptAnswerDB).where(
                PlacementAttemptAnswerDB.attempt_id == attempt_id,
                PlacementAttemptAnswerDB.question_id.in_(writing_ids),
            )
        )
    ).scalars().all()
    return float(sum(float(r.score or 0) for r in rows))


async def _seed_reading_mastery(db: AsyncSession, user_id: int, attempt_id: int) -> None:
    rows = (
        await db.execute(
            select(PlacementAttemptAnswerDB).where(
                PlacementAttemptAnswerDB.attempt_id == attempt_id,
                PlacementAttemptAnswerDB.is_correct.is_(True),
                PlacementAttemptAnswerDB.skill_id.is_not(None),
            )
        )
    ).scalars().all()
    for row in rows:
        await apply_answer(db, user_id, int(row.skill_id), correct=True)


# Deprecated adaptive name kept for any leftover imports during migration
async def submit_session_answer(*_args, **_kwargs) -> dict[str, Any]:
    raise RuntimeError("Adaptive placement answers are removed; use reading/writing endpoints")
