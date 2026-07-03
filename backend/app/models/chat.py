from sqlalchemy import (
    Column, BigInteger, SmallInteger, Integer, TIMESTAMP,
    TEXT, ForeignKey, func, JSON,
)
from sqlalchemy.orm import relationship
from app.core.database import Base
from app.models.enums import session_status_enum, message_role_enum


#  chat_sessions

class ChatSessionDB(Base):
    __tablename__ = "chat_sessions"

    id               = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id          = Column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    scenario_id      = Column(BigInteger, ForeignKey("scenarios.id", ondelete="RESTRICT"), nullable=False, index=True)
    status           = Column(session_status_enum, nullable=False)
    clarity_score    = Column(SmallInteger, nullable=True)           # 0-100
    message_count    = Column(SmallInteger, default=0, nullable=False)
    duration_sec     = Column(Integer, default=0, nullable=False)
    feedback_summary = Column(JSON, nullable=True)
    started_at       = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())
    ended_at         = Column(TIMESTAMP(timezone=True), nullable=True)

    user       = relationship("UserDB", back_populates="chat_sessions")
    scenario   = relationship("ScenarioDB", back_populates="chat_sessions")
    messages   = relationship("ChatMessageDB", back_populates="session", cascade="all, delete-orphan")
    vocabulary = relationship("VocabularyBankDB", back_populates="session")


# Chat messages

class ChatMessageDB(Base):
    __tablename__ = "chat_messages"

    id         = Column(BigInteger, primary_key=True, autoincrement=True)
    session_id = Column(BigInteger, ForeignKey("chat_sessions.id", ondelete="CASCADE"), nullable=False, index=True)
    role       = Column(message_role_enum, nullable=False)
    content    = Column(TEXT, nullable=False)
    feedback   = Column(JSON, nullable=True)
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())

    session = relationship("ChatSessionDB", back_populates="messages")