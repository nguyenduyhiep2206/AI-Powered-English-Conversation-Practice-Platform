import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pydantic import ValidationError

from app.api.roadmap import AssembleRequest
from app.services import roadmap_assembler_service as ras
from app.services.roadmap_assembler_service import select_skills_for_roadmap


def test_select_respects_max_steps_as_horizon():
    skills = [
        {
            "id": i,
            "slug": f"s{i}",
            "title": f"s{i}",
            "cefr_level": "A1",
            "skill_type": "grammar",
            "is_active": True,
            "difficulty_in_level": i,
        }
        for i in range(1, 8)
    ]
    selected = select_skills_for_roadmap(
        skills,
        mastery={i: 0.2 for i in range(1, 8)},
        placement_score=1,
        prereq_from_by_to={},
        max_steps=3,
    )
    assert len(selected) == 3


def test_plan_next_steps_excludes_assigned_ids_via_filter():
    assigned = {1, 2}
    skills = [{"id": 1}, {"id": 2}, {"id": 3}, {"id": 4}]
    remaining = [s for s in skills if int(s["id"]) not in assigned]
    assert [s["id"] for s in remaining] == [3, 4]


def test_load_assigned_skill_ids_query_shape():
    db = AsyncMock()
    result = MagicMock()
    result.scalars.return_value.all.return_value = [10, 20]
    db.execute = AsyncMock(return_value=result)
    ids = asyncio.run(ras._load_assigned_skill_ids(db, user_id=1))
    assert ids == {10, 20}


def test_plan_next_steps_returns_empty_when_no_candidates():
    async def run():
        db = AsyncMock()
        profile = MagicMock()
        profile.user_id = 1
        profile.placement_score = 1
        profile.weak_point = None
        profile.current_level = ras.CEFRLevel.A1

        skill = MagicMock()
        skill.id = 1

        with (
            patch.object(ras, "_require_profile", AsyncMock(return_value=profile)),
            patch.object(ras, "load_active_skills", AsyncMock(return_value=[skill])),
            patch.object(ras, "_load_assigned_skill_ids", AsyncMock(return_value={1})),
            patch.object(ras, "load_mastery_map", AsyncMock(return_value={1: 0.2})),
        ):
            selected, mastery, out_profile, target_level = await ras.plan_next_steps(
                db, user_id=1
            )
            assert selected == []
            assert mastery == {1: 0.2}
            assert out_profile is profile
            assert target_level == ras.CEFRLevel.A1

    asyncio.run(run())


def test_assemble_request_defaults_to_three_and_clamps_api_range():
    assert AssembleRequest().max_steps == 3
    assert AssembleRequest(max_steps=1).max_steps == 1
    assert AssembleRequest(max_steps=5).max_steps == 5
    with pytest.raises(ValidationError):
        AssembleRequest(max_steps=0)
    with pytest.raises(ValidationError):
        AssembleRequest(max_steps=6)


def test_next_week_number_from_existing_weeks():
    db = AsyncMock()
    result = MagicMock()
    result.scalars.return_value.all.return_value = [1, 2]
    db.execute = AsyncMock(return_value=result)

    assert asyncio.run(ras._next_week_number(db, user_id=1)) == 3


def test_next_week_number_starts_at_one_without_existing_weeks():
    db = AsyncMock()
    result = MagicMock()
    result.scalars.return_value.all.return_value = []
    db.execute = AsyncMock(return_value=result)

    assert asyncio.run(ras._next_week_number(db, user_id=1)) == 1


def test_replan_locked_tail_marks_only_first_new_week_current():
    async def run():
        db = AsyncMock()
        progress_result = MagicMock()
        progress_result.scalar_one_or_none.return_value = None
        db.execute.return_value = progress_result
        profile = MagicMock(goal=ras.GoalEnum.travel)
        selected = [{"id": 10}, {"id": 11}, {"id": 12}]
        scenario = MagicMock()
        persist = AsyncMock(
            side_effect=[
                {"week_number": 4},
                {"week_number": 5},
                {"week_number": 6},
            ]
        )

        with (
            patch.object(ras, "_delete_locked_tail", AsyncMock()) as delete_tail,
            patch.object(
                ras,
                "plan_next_steps",
                AsyncMock(
                    return_value=(
                        selected,
                        {10: 0.2},
                        profile,
                        ras.CEFRLevel.A1,
                    )
                ),
            ),
            patch.object(ras, "pick_scenario", AsyncMock(return_value=scenario)),
            patch.object(ras, "_next_week_number", AsyncMock(return_value=4)),
            patch.object(ras, "_persist_week", persist),
            patch.object(ras, "get_user_roadmap", AsyncMock(return_value=["roadmap"])),
        ):
            result = await ras.replan_locked_tail(db, user_id=7, horizon=3, commit=False)

        delete_tail.assert_awaited_once_with(db, 7)
        assert [call.kwargs["is_current"] for call in persist.await_args_list] == [
            True,
            False,
            False,
        ]
        assert [call.args[2] for call in persist.await_args_list] == [4, 5, 6]
        db.commit.assert_not_awaited()
        assert result == ["roadmap"]

    asyncio.run(run())


def test_replan_locked_tail_keeps_new_weeks_locked_when_current_exists():
    async def run():
        db = AsyncMock()
        progress_result = MagicMock()
        progress_result.scalar_one_or_none.return_value = 42
        db.execute.return_value = progress_result
        profile = MagicMock(goal=ras.GoalEnum.travel)
        selected = [{"id": 10}, {"id": 11}]
        scenario = MagicMock()
        plan = AsyncMock(
            return_value=(selected, {10: 0.2}, profile, ras.CEFRLevel.A1)
        )
        persist = AsyncMock()

        with (
            patch.object(ras, "_delete_locked_tail", AsyncMock()),
            patch.object(ras, "plan_next_steps", plan),
            patch.object(ras, "pick_scenario", AsyncMock(return_value=scenario)),
            patch.object(ras, "_next_week_number", AsyncMock(return_value=4)),
            patch.object(ras, "_persist_week", persist),
            patch.object(ras, "get_user_roadmap", AsyncMock(return_value=["roadmap"])),
        ):
            await ras.replan_locked_tail(db, user_id=7, horizon=3, commit=False)

        assert [call.kwargs["is_current"] for call in persist.await_args_list] == [
            False,
            False,
        ]
        plan.assert_awaited_once_with(db, 7, horizon=2)

    asyncio.run(run())


def test_replan_empty_selection_keeps_tail_delete_and_honors_commit():
    async def run():
        db = AsyncMock()
        progress_result = MagicMock()
        progress_result.scalar_one_or_none.return_value = None
        db.execute.return_value = progress_result
        profile = MagicMock()
        get_roadmap = AsyncMock(return_value=[{"status": "completed"}])

        with (
            patch.object(ras, "_delete_locked_tail", AsyncMock()) as delete_tail,
            patch.object(
                ras,
                "plan_next_steps",
                AsyncMock(
                    return_value=([], {}, profile, ras.CEFRLevel.A1)
                ),
            ),
            patch.object(ras, "get_user_roadmap", get_roadmap),
        ):
            result = await ras.replan_locked_tail(db, user_id=7)

        delete_tail.assert_awaited_once_with(db, 7)
        db.commit.assert_awaited_once()
        get_roadmap.assert_awaited_once_with(db, 7)
        assert result == [{"status": "completed"}]

    asyncio.run(run())
