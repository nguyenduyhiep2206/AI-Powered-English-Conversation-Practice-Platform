"""
PostgreSQL native ENUM types.

Define all enums here so they are created once in the DB and reused
across models — avoids duplicate type errors on create_all().
"""
import enum
from sqlalchemy import Enum as SAEnum


# CEFR level
class CEFRLevel(str, enum.Enum):
    A1 = "A1"
    A2 = "A2"
    B1 = "B1"
    B2 = "B2"
    C1 = "C1"


cefr_level_enum = SAEnum(CEFRLevel, name="cefr_level", create_type=True)


# User profile
class GoalEnum(str, enum.Enum):
    job_interview       = "job_interview"
    daily_conversation  = "daily_conversation"
    travel              = "travel"
    ielts               = "ielts"
    business            = "business"
    work                = "work"
    school              = "school"
    culture             = "culture"
    family              = "family"
    challenge           = "challenge"
    other               = "other"


class WeakPointEnum(str, enum.Enum):
    grammar     = "grammar"
    vocabulary  = "vocabulary"
    confidence  = "confidence"
    writing     = "writing"


goal_enum       = SAEnum(GoalEnum, name="goal_enum", create_type=True)
weak_point_enum = SAEnum(WeakPointEnum, name="weak_point_enum", create_type=True)


class SurveyQuestionTypeEnum(str, enum.Enum):
    single_choice = "single_choice"
    text = "text"


survey_question_type_enum = SAEnum(
    SurveyQuestionTypeEnum, name="survey_question_type_enum", create_type=True
)


# Scenario
class ScenarioCategoryEnum(str, enum.Enum):
    job_interview   = "job_interview"
    hotel           = "hotel"
    restaurant      = "restaurant"
    shopping        = "shopping"
    travel          = "travel"
    small_talk      = "small_talk"
    medical         = "medical"
    custom          = "custom"


scenario_category_enum = SAEnum(ScenarioCategoryEnum, name="scenario_category_enum", create_type=True)


# Roadmap / Progress
class ProgressStatusEnum(str, enum.Enum):
    locked      = "locked"
    in_progress = "in_progress"
    completed   = "completed"


progress_status_enum = SAEnum(ProgressStatusEnum, name="progress_status_enum", create_type=True)


# Book (admin PDF uploads)
class BookTypeEnum(str, enum.Enum):
    grammar_textbook = "grammar_textbook"
    reading_practice = "reading_practice"
    test_bank = "test_bank"
    freeform = "freeform"


class BookStatusEnum(str, enum.Enum):
    uploaded = "uploaded"
    needs_review = "needs_review"
    processing = "processing"
    ready = "ready"
    failed = "failed"


book_type_enum = SAEnum(BookTypeEnum, name="book_type_enum", create_type=True)
book_status_enum = SAEnum(BookStatusEnum, name="book_status_enum", create_type=True)


# Level-first quiz / skill graph
class QuizQuestionTypeEnum(str, enum.Enum):
    mcq = "mcq"
    cloze = "cloze"
    fix_grammar = "fix_grammar"
    writing = "writing"


class QuizQuestionStatusEnum(str, enum.Enum):
    draft = "draft"
    published = "published"
    rejected = "rejected"


class SkillTypeEnum(str, enum.Enum):
    grammar = "grammar"
    vocabulary = "vocabulary"
    reading = "reading"
    functional = "functional"


class ToeicPartEnum(str, enum.Enum):
    r5 = "r5"
    r6 = "r6"
    r7 = "r7"
    w1 = "w1"
    w2 = "w2"
    w3 = "w3"


quiz_question_type_enum = SAEnum(
    QuizQuestionTypeEnum, name="quiz_question_type_enum", create_type=True
)
quiz_question_status_enum = SAEnum(
    QuizQuestionStatusEnum, name="quiz_question_status_enum", create_type=True
)
skill_type_enum = SAEnum(SkillTypeEnum, name="skill_type_enum", create_type=True)
toeic_part_enum = SAEnum(ToeicPartEnum, name="toeic_part_enum", create_type=True)


class PlacementAttemptStatusEnum(str, enum.Enum):
    in_progress = "in_progress"
    completed = "completed"
    abandoned = "abandoned"


placement_attempt_status_enum = SAEnum(
    PlacementAttemptStatusEnum,
    name="placement_attempt_status_enum",
    create_type=True,
)