from sqlalchemy import (
    BigInteger,
    Boolean,
    Column,
    Float,
    ForeignKey,
    Integer,
    SmallInteger,
    String,
    Text,
    TIMESTAMP,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSON

from app.core.database import Base
from app.models.enums import cefr_level_enum, placement_attempt_status_enum


class PlacementAttemptDB(Base):
    __tablename__ = "placement_attempts"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id = Column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    status = Column(placement_attempt_status_enum, nullable=False)
    form_snapshot = Column(JSON, nullable=True)
    section = Column(String(20), nullable=False, server_default="reading")
    section_ends_at = Column(TIMESTAMP(timezone=True), nullable=True)
    reading_raw = Column(Integer, nullable=True)
    reading_scale = Column(Integer, nullable=True)
    writing_raw = Column(Float, nullable=True)
    writing_scale = Column(Integer, nullable=True)
    # Legacy adaptive columns (unused by TOEIC session; kept nullable for old rows)
    ability_index = Column(Float, nullable=True)
    confidence = Column(Float, nullable=True)
    questions_asked = Column(Integer, nullable=False, default=0, server_default="0")
    seen_question_ids = Column(JSON, nullable=False, default=list)
    current_question_id = Column(
        BigInteger, ForeignKey("quiz_questions.id", ondelete="SET NULL"), nullable=True
    )
    weak_point_bias = Column(String(50), nullable=True)
    result_level = Column(cefr_level_enum, nullable=True)
    result_sublevel = Column(SmallInteger, nullable=True)
    started_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())
    completed_at = Column(TIMESTAMP(timezone=True), nullable=True)


class PlacementAttemptAnswerDB(Base):
    __tablename__ = "placement_attempt_answers"
    __table_args__ = (
        UniqueConstraint("attempt_id", "question_id", name="uq_placement_attempt_question"),
    )

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    attempt_id = Column(
        BigInteger, ForeignKey("placement_attempts.id", ondelete="CASCADE"), nullable=False
    )
    question_id = Column(
        BigInteger, ForeignKey("quiz_questions.id", ondelete="CASCADE"), nullable=False
    )
    skill_id = Column(BigInteger, nullable=True)
    cefr_level = Column(cefr_level_enum, nullable=True)
    given_answer = Column(Text, nullable=False)
    is_correct = Column(Boolean, nullable=True)
    score = Column(Float, nullable=True)
    ai_scores = Column(JSON, nullable=True)
    ai_feedback = Column(Text, nullable=True)
    ability_after = Column(Float, nullable=True)
    confidence_after = Column(Float, nullable=True)
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())
