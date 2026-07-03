from sqlalchemy import (
    Column, BigInteger, SmallInteger, Boolean, TIMESTAMP, DATE,
    TEXT, ForeignKey, func, String, JSON, UniqueConstraint,
)
from sqlalchemy.orm import relationship
from app.core.database import Base
from app.models.enums import (
    register_enum,
    vocab_source_enum,
    selection_status_enum,
    exercise_status_enum,
)


#  vocabulary_bank

class VocabularyBankDB(Base):
    __tablename__ = "vocabulary_bank"

    id             = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id        = Column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    word           = Column(String(150), nullable=False)
    definition     = Column(TEXT, nullable=False)
    example        = Column(TEXT, nullable=True)
    synonyms       = Column(JSON, nullable=True)
    register       = Column(register_enum, nullable=True)
    source         = Column(vocab_source_enum, nullable=False)
    session_id     = Column(BigInteger, ForeignKey("chat_sessions.id", ondelete="SET NULL"), nullable=True, index=True)
    srs_level      = Column(SmallInteger, default=0, nullable=False)
    next_review    = Column(DATE, nullable=True)
    review_count   = Column(SmallInteger, default=0, nullable=False)
    correct_streak = Column(SmallInteger, default=0, nullable=False)
    created_at     = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())
    updated_at     = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    user          = relationship("UserDB", back_populates="vocabulary")
    session       = relationship("ChatSessionDB", back_populates="vocabulary")
    story_items   = relationship("StoryVocabItemDB", back_populates="vocab")
    story_answers = relationship("StoryAnswerDB", back_populates="vocab")


#  story_vocab_selections

class StoryVocabSelectionDB(Base):
    __tablename__ = "story_vocab_selections"

    id         = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id    = Column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    name       = Column(String(150), nullable=True)
    status     = Column(selection_status_enum, nullable=False, default="draft")
    word_count = Column(SmallInteger, default=0, nullable=False)
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    user      = relationship("UserDB", back_populates="story_selections")
    items     = relationship("StoryVocabItemDB", back_populates="selection", cascade="all, delete-orphan")
    exercises = relationship("StoryExerciseDB", back_populates="selection")


#  story_vocab_items

class StoryVocabItemDB(Base):
    __tablename__ = "story_vocab_items"
    __table_args__ = (
        UniqueConstraint("selection_id", "vocab_id", name="uq_selection_vocab"),
    )

    id           = Column(BigInteger, primary_key=True, autoincrement=True)
    selection_id = Column(BigInteger, ForeignKey("story_vocab_selections.id", ondelete="CASCADE"), nullable=False, index=True)
    vocab_id     = Column(BigInteger, ForeignKey("vocabulary_bank.id", ondelete="CASCADE"), nullable=False, index=True)
    added_at     = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())

    selection = relationship("StoryVocabSelectionDB", back_populates="items")
    vocab     = relationship("VocabularyBankDB", back_populates="story_items")


#  story_exercises

class StoryExerciseDB(Base):
    __tablename__ = "story_exercises"

    id           = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id      = Column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    selection_id = Column(BigInteger, ForeignKey("story_vocab_selections.id", ondelete="RESTRICT"), nullable=False, index=True)
    title        = Column(String(255), nullable=False)
    content      = Column(TEXT, nullable=False)
    blanks       = Column(JSON, nullable=False)
    total_blanks = Column(SmallInteger, default=0, nullable=False)
    status       = Column(exercise_status_enum, nullable=False, default="pending")
    score        = Column(SmallInteger, nullable=True)
    generated_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())
    completed_at = Column(TIMESTAMP(timezone=True), nullable=True)

    user      = relationship("UserDB", back_populates="story_exercises")
    selection = relationship("StoryVocabSelectionDB", back_populates="exercises")
    answers   = relationship("StoryAnswerDB", back_populates="exercise", cascade="all, delete-orphan")


#  story_answers

class StoryAnswerDB(Base):
    __tablename__ = "story_answers"
    __table_args__ = (
        UniqueConstraint("exercise_id", "blank_pos", name="uq_exercise_blank_pos"),
    )

    id          = Column(BigInteger, primary_key=True, autoincrement=True)
    exercise_id = Column(BigInteger, ForeignKey("story_exercises.id",  ondelete="CASCADE"),  nullable=False, index=True)
    vocab_id    = Column(BigInteger, ForeignKey("vocabulary_bank.id",  ondelete="RESTRICT"), nullable=False)
    blank_pos   = Column(SmallInteger, nullable=False)
    user_answer = Column(String(255), nullable=False)
    is_correct  = Column(Boolean, nullable=False)
    ai_feedback = Column(TEXT, nullable=True)
    answered_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())

    exercise = relationship("StoryExerciseDB", back_populates="answers")
    vocab    = relationship("VocabularyBankDB", back_populates="story_answers")