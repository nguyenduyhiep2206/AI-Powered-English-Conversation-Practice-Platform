# Import order:
#   1. enums       — no dependencies
#   2. user        — no FK deps (other tables point TO users)
#   3. auth        — depends on users
#   4. profile     — depends on users
#   5. scenario    — no user FK at model level, but user_progress does
#
# Every model must be imported here so SQLAlchemy's mapper registry can
# resolve string-based relationship targets before init_db() runs.

from app.models.enums import *

from app.models.user import UserDB

from app.models.auth import (
    RoleDB,
    PermissionDB,
    RefreshTokenDB,
    user_roles_table,
    role_permissions_table,
)

from app.models.profile import UserProfileDB

from app.models.survey import SurveyQuestionDB

from app.models.book import BookDB

from app.models.book_structure_preview import BookStructurePreviewDB

from app.models.learning_skill import LearningSkillDB, SkillEdgeDB

from app.models.book_skill_source import BookSkillSourceDB

from app.models.quiz_passage import QuizPassageDB

from app.models.quiz_question import QuizQuestionDB

from app.models.placement_attempt import PlacementAttemptDB, PlacementAttemptAnswerDB

from app.models.user_skill_mastery import UserSkillMasteryDB

from app.models.skill_lesson import (
    SkillLessonDB,
    UserLessonPackProgressDB,
    UserLessonProgressDB,
)

from app.models.theme_unit import LearningThemeUnitDB, ThemeUnitSkillDB

from app.models.roadmap_step_skill import RoadmapStepSkillDB

from app.models.scenario import (
    ScenarioDB,
    RoadmapStepDB,
    UserProgressDB,
)

from app.models.tutor import TutorMessageDB, TutorSessionDB

from app.models.lesson_qa import LessonQaMessageDB, LessonQaSessionDB

__all__ = [
    # Auth & RBAC
    "UserDB", "RoleDB", "PermissionDB", "RefreshTokenDB",
    "user_roles_table", "role_permissions_table",
    # Profile & Onboarding
    "UserProfileDB", "SurveyQuestionDB", "BookDB", "BookStructurePreviewDB",
    # Level-first skill graph & quiz bank
    "LearningSkillDB", "SkillEdgeDB", "BookSkillSourceDB",
    "QuizPassageDB", "QuizQuestionDB", "PlacementAttemptDB", "PlacementAttemptAnswerDB",
    "UserSkillMasteryDB", "SkillLessonDB", "UserLessonProgressDB", "UserLessonPackProgressDB",
    "LearningThemeUnitDB", "ThemeUnitSkillDB", "RoadmapStepSkillDB",
    # Scenario & Roadmap
    "ScenarioDB", "RoadmapStepDB", "UserProgressDB",
    # AI Tutor
    "TutorSessionDB", "TutorMessageDB",
    # Lesson Q&A
    "LessonQaSessionDB", "LessonQaMessageDB",
]