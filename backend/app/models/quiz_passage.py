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
from app.models.enums import quiz_question_status_enum, toeic_part_enum


class QuizPassageDB(Base):
    __tablename__ = "quiz_passages"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    book_id = Column(BigInteger, ForeignKey("books.id", ondelete="SET NULL"), nullable=True, index=True)
    unit_id = Column(
        BigInteger,
        ForeignKey("book_structure_preview.id", ondelete="SET NULL"),
        nullable=True,
    )
    toeic_part = Column(toeic_part_enum, nullable=False, index=True)
    body = Column(TEXT, nullable=False)
    media_url = Column(String(1000), nullable=True)
    status = Column(quiz_question_status_enum, nullable=False, server_default="draft")
    meta = Column(JSON, nullable=True)
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(
        TIMESTAMP(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )
