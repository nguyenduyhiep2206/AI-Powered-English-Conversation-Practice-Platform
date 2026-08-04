from sqlalchemy import (
    BigInteger,
    Column,
    ForeignKey,
    SmallInteger,
    Text,
    TIMESTAMP,
    func,
)
from sqlalchemy.dialects.postgresql import JSON

from app.core.database import Base
from app.models.enums import tutor_message_role_enum, tutor_session_status_enum


class TutorSessionDB(Base):
    __tablename__ = "tutor_sessions"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id = Column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    roadmap_step_id = Column(
        BigInteger,
        ForeignKey("roadmap_steps.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    scenario_id = Column(
        BigInteger, ForeignKey("scenarios.id", ondelete="RESTRICT"), nullable=False
    )
    status = Column(tutor_session_status_enum, nullable=False)
    target_skill_ids = Column(JSON, nullable=False)  # list[int]
    message_count = Column(SmallInteger, nullable=False, default=0)  # user turns
    summary = Column(JSON, nullable=True)
    started_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())
    ended_at = Column(TIMESTAMP(timezone=True), nullable=True)
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


class TutorMessageDB(Base):
    __tablename__ = "tutor_messages"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    session_id = Column(
        BigInteger,
        ForeignKey("tutor_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    role = Column(tutor_message_role_enum, nullable=False)
    content = Column(Text, nullable=False)
    meta = Column(JSON, nullable=True)
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())
