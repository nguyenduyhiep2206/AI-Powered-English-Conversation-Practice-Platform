from sqlalchemy import (
    BigInteger,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship

from app.core.database import Base


class SkillLessonDB(Base):
    __tablename__ = "skill_lessons"
    __table_args__ = (
        UniqueConstraint("skill_id", "pack_index", name="uq_skill_lessons_skill_pack"),
    )

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    skill_id = Column(
        BigInteger,
        ForeignKey("learning_skills.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    pack_index = Column(Integer, nullable=False, server_default="0")
    title = Column(String(500), nullable=False)
    objective = Column(Text, nullable=False)
    content = Column(JSONB, nullable=False)
    source = Column(String(20), nullable=False, server_default="llm_reviewed")
    status = Column(String(20), nullable=False, server_default="draft")
    book_source_id = Column(
        BigInteger,
        ForeignKey("book_skill_sources.id", ondelete="SET NULL"),
        nullable=True,
    )
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    skill = relationship("LearningSkillDB")
    book_source = relationship("BookSkillSourceDB")


class UserLessonProgressDB(Base):
    __tablename__ = "user_lesson_progress"
    __table_args__ = (UniqueConstraint("user_id", "skill_id", name="uq_user_lesson_progress"),)

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id = Column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    skill_id = Column(
        BigInteger,
        ForeignKey("learning_skills.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    completed_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class UserLessonPackProgressDB(Base):
    """Per micro-lesson completion inside a LessonPack."""

    __tablename__ = "user_lesson_pack_progress"
    __table_args__ = (
        UniqueConstraint(
            "user_id", "skill_id", "pack_index", name="uq_user_lesson_pack_progress"
        ),
    )

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id = Column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    skill_id = Column(
        BigInteger,
        ForeignKey("learning_skills.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    pack_index = Column(Integer, nullable=False)
    completed_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
