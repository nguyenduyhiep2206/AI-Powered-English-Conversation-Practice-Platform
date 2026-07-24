import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

from app.models.enums import ProgressStatusEnum
from app.services.mastery_service import MASTERY_STRONG
from app.services.roadmap_progress_service import can_pass_week, complete_roadmap_week


def test_pass_khi_mastery_du():
    assert can_pass_week(0.7) is True
    assert can_pass_week(MASTERY_STRONG) is True
    assert can_pass_week(0.69) is False
    assert can_pass_week(0.0) is False


def test_complete_flow_should_replan_instead_of_only_unlock():
    async def run():
        db = AsyncMock()
        progress = MagicMock()
        progress.status = ProgressStatusEnum.in_progress
        step = MagicMock(week_number=1)
        replan = AsyncMock(
            return_value=[
                {"roadmap_step_id": 99, "status": "locked"},
                {"roadmap_step_id": 100, "status": "in_progress"},
            ]
        )

        with (
            patch(
                "app.services.roadmap_progress_service._require_in_progress",
                AsyncMock(return_value=(progress, step)),
            ),
            patch(
                "app.services.roadmap_progress_service._quiz_skill_id",
                AsyncMock(return_value=5),
            ),
            patch(
                "app.services.roadmap_progress_service._mastery_for_skill",
                AsyncMock(return_value=0.8),
            ),
            patch(
                "app.services.roadmap_progress_service.replan_locked_tail",
                replan,
            ),
        ):
            result = await complete_roadmap_week(db, user_id=1, roadmap_step_id=10)

        assert progress.status == ProgressStatusEnum.completed
        assert progress.completed_at is not None
        db.flush.assert_awaited_once()
        replan.assert_awaited_once_with(db, 1, commit=False)
        db.commit.assert_awaited_once()
        assert result["unlocked_step_id"] == 100
        assert result["replanned"] is True
        assert result["step_id"] == 10
        assert result["status"] == ProgressStatusEnum.completed.value

    asyncio.run(run())


def test_complete_returns_none_unlocked_when_replan_has_no_in_progress():
    async def run():
        db = AsyncMock()
        progress = MagicMock()
        progress.status = ProgressStatusEnum.in_progress
        step = MagicMock(week_number=2)
        replan = AsyncMock(
            return_value=[
                {"roadmap_step_id": 50, "status": "locked"},
                {"roadmap_step_id": 51, "status": "locked"},
            ]
        )

        with (
            patch(
                "app.services.roadmap_progress_service._require_in_progress",
                AsyncMock(return_value=(progress, step)),
            ),
            patch(
                "app.services.roadmap_progress_service._quiz_skill_id",
                AsyncMock(return_value=3),
            ),
            patch(
                "app.services.roadmap_progress_service._mastery_for_skill",
                AsyncMock(return_value=MASTERY_STRONG),
            ),
            patch(
                "app.services.roadmap_progress_service.replan_locked_tail",
                replan,
            ),
        ):
            result = await complete_roadmap_week(db, user_id=7, roadmap_step_id=5)

        assert result["unlocked_step_id"] is None
        assert result["replanned"] is True

    asyncio.run(run())
