from app.models.enums import GoalEnum, ScenarioCategoryEnum
from app.services.roadmap_assembler_service import GOAL_TO_CATEGORY


def test_busuu_goals_map_to_scenario_categories():
    assert GOAL_TO_CATEGORY[GoalEnum.work] == ScenarioCategoryEnum.job_interview
    assert GOAL_TO_CATEGORY[GoalEnum.school] == ScenarioCategoryEnum.custom
    assert GOAL_TO_CATEGORY[GoalEnum.travel] == ScenarioCategoryEnum.travel
    assert GOAL_TO_CATEGORY[GoalEnum.culture] == ScenarioCategoryEnum.small_talk
    assert GOAL_TO_CATEGORY[GoalEnum.family] == ScenarioCategoryEnum.small_talk
    assert GOAL_TO_CATEGORY[GoalEnum.challenge] == ScenarioCategoryEnum.small_talk
    assert GOAL_TO_CATEGORY[GoalEnum.other] == ScenarioCategoryEnum.small_talk
