from sqlalchemy import (
    JSON,
    TEXT,
    BigInteger,
    Column,
    ForeignKey,
    String,
    TIMESTAMP,
    func,
)

from app.core.database import Base
from app.models.enums import (
    cefr_level_enum,
    quiz_question_status_enum,
    quiz_question_type_enum,
)


class QuizQuestionDB(Base):
    __tablename__ = "quiz_questions"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    skill_id = Column(
        BigInteger,
        ForeignKey("learning_skills.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    book_id = Column(BigInteger, ForeignKey("books.id", ondelete="CASCADE"), nullable=False, index=True)
    unit_id = Column(
        BigInteger,
        ForeignKey("book_structure_preview.id", ondelete="CASCADE"),
        nullable=False,
    )
    question_type = Column(quiz_question_type_enum, nullable=False)
    stem = Column(TEXT, nullable=False)
    passage = Column(TEXT, nullable=True)
    options = Column(JSON, nullable=True)
    answer = Column(String(500), nullable=False)
    explanation = Column(TEXT, nullable=True)
    cefr_level = Column(cefr_level_enum, nullable=True)
    difficulty = Column(String(20), nullable=False, server_default="medium")
    status = Column(quiz_question_status_enum, nullable=False, server_default="draft")
    generation_batch_id = Column(String(64), nullable=True, index=True)
    source_chunk_ids = Column(JSON, nullable=True)
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(
        TIMESTAMP(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )
