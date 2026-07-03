from sqlalchemy import (
    Column, BigInteger, SmallInteger, Integer, Boolean,
    TIMESTAMP, DATE, TEXT, ForeignKey, func, String, UniqueConstraint,
)
from sqlalchemy.orm import relationship
from app.core.database import Base
from app.models.enums import quiz_type_enum, notification_type_enum


#  quiz_sessions

class QuizSessionDB(Base):
    __tablename__ = "quiz_sessions"

    id         = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id    = Column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    quiz_type  = Column(quiz_type_enum, nullable=False)
    score      = Column(SmallInteger, default=0, nullable=False)
    total_q    = Column(SmallInteger, default=0, nullable=False)
    correct_q  = Column(SmallInteger, default=0, nullable=False)
    lives_used = Column(SmallInteger, default=0, nullable=False)
    completed  = Column(Boolean, default=False, nullable=False)
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())
    ended_at   = Column(TIMESTAMP(timezone=True), nullable=True)

    user = relationship("UserDB", back_populates="quiz_sessions")


# User streaks  (1-1 with users)

class UserStreakDB(Base):
    __tablename__ = "user_streaks"

    id              = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id         = Column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True)
    current_streak  = Column(SmallInteger, default=0, nullable=False)
    longest_streak  = Column(SmallInteger, default=0, nullable=False)
    last_activity   = Column(DATE, nullable=True)
    total_sessions  = Column(Integer, default=0, nullable=False)
    total_words     = Column(Integer, default=0, nullable=False)
    updated_at      = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    user = relationship("UserDB", back_populates="streak")


#  user_badges

class UserBadgeDB(Base):
    __tablename__ = "user_badges"
    __table_args__ = (
        UniqueConstraint("user_id", "badge_code", name="uq_user_badge"),
    )

    id         = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id    = Column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    badge_code = Column(String(100), nullable=False)
    badge_name = Column(String(150), nullable=False)
    earned_at  = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())

    user = relationship("UserDB", back_populates="badges")


#  notifications

class NotificationDB(Base):
    __tablename__ = "notifications"

    id         = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id    = Column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    type       = Column(notification_type_enum, nullable=False)
    title      = Column(String(255), nullable=False)
    body       = Column(TEXT, nullable=True)
    is_read    = Column(Boolean, default=False, nullable=False)
    send_at    = Column(TIMESTAMP(timezone=True), nullable=False)
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())

    user = relationship("UserDB", back_populates="notifications")