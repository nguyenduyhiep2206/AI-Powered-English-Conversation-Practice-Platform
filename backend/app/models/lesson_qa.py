from sqlalchemy import (
    BigInteger,
    Column,
    ForeignKey,
    SmallInteger,
    Text,
    TIMESTAMP,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSON

from app.core.database import Base
from app.models.enums import lesson_qa_message_role_enum, lesson_qa_session_status_enum


class LessonQaSessionDB(Base):
    __tablename__ = "lesson_qa_sessions"
    __table_args__ = (
        UniqueConstraint("user_id", "skill_id", name="uq_lesson_qa_user_skill"),
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
    status = Column(lesson_qa_session_status_enum, nullable=False)
    message_count = Column(SmallInteger, nullable=False, default=0)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        TIMESTAMP(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class LessonQaMessageDB(Base):
    __tablename__ = "lesson_qa_messages"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    session_id = Column(
        BigInteger,
        ForeignKey("lesson_qa_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    role = Column(lesson_qa_message_role_enum, nullable=False)
    content = Column(Text, nullable=False)
    meta = Column(JSON, nullable=True)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)
