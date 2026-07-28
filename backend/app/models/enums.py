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


# Chat session
class SessionStatusEnum(str, enum.Enum):
    active      = "active"
    completed   = "completed"
    abandoned   = "abandoned"


session_status_enum = SAEnum(SessionStatusEnum, name="session_status_enum", create_type=True)


# Chat message
class MessageRoleEnum(str, enum.Enum):
    user        = "user"
    assistant   = "assistant"


message_role_enum = SAEnum(MessageRoleEnum, name="message_role_enum", create_type=True)


# Vocabulary
class RegisterEnum(str, enum.Enum):
    formal      = "formal"
    informal    = "informal"
    neutral     = "neutral"
    technical   = "technical"


class VocabSourceEnum(str, enum.Enum):
    chat        = "chat"
    suggestion  = "suggestion"
    bookmark    = "bookmark"
    quiz        = "quiz"


register_enum    = SAEnum(RegisterEnum, name="register_enum", create_type=True)
vocab_source_enum = SAEnum(VocabSourceEnum, name="vocab_source_enum", create_type=True)


# Story
class SelectionStatusEnum(str, enum.Enum):
    draft       = "draft"
    generating  = "generating"
    generated   = "generated"
    archived    = "archived"


class ExerciseStatusEnum(str, enum.Enum):
    pending     = "pending"
    in_progress = "in_progress"
    completed   = "completed"


selection_status_enum = SAEnum(SelectionStatusEnum, name="selection_status_enum", create_type=True)
exercise_status_enum  = SAEnum(ExerciseStatusEnum, name="exercise_status_enum", create_type=True)


# Quiz
class QuizTypeEnum(str, enum.Enum):
    word_snap           = "word_snap"
    fix_the_chat        = "fix_the_chat"
    context_challenge   = "context_challenge"
    streak_quiz         = "streak_quiz"


quiz_type_enum = SAEnum(QuizTypeEnum, name="quiz_type_enum", create_type=True)


# Notification
class NotificationTypeEnum(str, enum.Enum):
    daily_reminder  = "daily_reminder"
    streak_alert    = "streak_alert"
    milestone       = "milestone"
    weekly_digest   = "weekly_digest"


notification_type_enum = SAEnum(NotificationTypeEnum, name="notification_type_enum", create_type=True)


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


class QuizQuestionStatusEnum(str, enum.Enum):
    draft = "draft"
    published = "published"
    rejected = "rejected"


class SkillTypeEnum(str, enum.Enum):
    grammar = "grammar"
    vocabulary = "vocabulary"
    reading = "reading"
    functional = "functional"


quiz_question_type_enum = SAEnum(
    QuizQuestionTypeEnum, name="quiz_question_type_enum", create_type=True
)
quiz_question_status_enum = SAEnum(
    QuizQuestionStatusEnum, name="quiz_question_status_enum", create_type=True
)
skill_type_enum = SAEnum(SkillTypeEnum, name="skill_type_enum", create_type=True)


class PlacementAttemptStatusEnum(str, enum.Enum):
    in_progress = "in_progress"
    completed = "completed"
    abandoned = "abandoned"


placement_attempt_status_enum = SAEnum(
    PlacementAttemptStatusEnum,
    name="placement_attempt_status_enum",
    create_type=True,
)