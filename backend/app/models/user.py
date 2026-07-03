from sqlalchemy import Column, String, Boolean, BigInteger, TIMESTAMP, func
from sqlalchemy.orm import relationship
from app.core.database import Base


class UserDB(Base):
    __tablename__ = "users"

    id            = Column(BigInteger, primary_key=True, autoincrement=True)
    username      = Column(String(50), unique=True, index=True, nullable=False)
    email         = Column(String(100), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=True)
    full_name     = Column(String(100), nullable=True)
    avatar_url    = Column(String(512), nullable=True)
    is_active     = Column(Boolean, default=True, nullable=False)
    auth_provider = Column(String(20), nullable=False, server_default="local")
    created_at    = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())
    updated_at    = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    # Relationships
    roles            = relationship("RoleDB", secondary="user_roles", back_populates="users")
    refresh_tokens   = relationship("RefreshTokenDB", back_populates="user", cascade="all, delete-orphan")
    profile          = relationship("UserProfileDB", back_populates="user", uselist=False, cascade="all, delete-orphan")
    progress         = relationship("UserProgressDB", back_populates="user", cascade="all, delete-orphan")
    chat_sessions    = relationship("ChatSessionDB", back_populates="user", cascade="all, delete-orphan")
    vocabulary       = relationship("VocabularyBankDB", back_populates="user", cascade="all, delete-orphan")
    story_selections = relationship("StoryVocabSelectionDB", back_populates="user", cascade="all, delete-orphan")
    story_exercises  = relationship("StoryExerciseDB", back_populates="user", cascade="all, delete-orphan")
    quiz_sessions    = relationship("QuizSessionDB", back_populates="user", cascade="all, delete-orphan")
    streak           = relationship("UserStreakDB", back_populates="user", uselist=False, cascade="all, delete-orphan")
    badges           = relationship("UserBadgeDB", back_populates="user", cascade="all, delete-orphan")
    notifications    = relationship("NotificationDB", back_populates="user", cascade="all, delete-orphan")