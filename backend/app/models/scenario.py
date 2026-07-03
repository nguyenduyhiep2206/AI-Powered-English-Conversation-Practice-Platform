from sqlalchemy import (
    Column, BigInteger, SmallInteger, Boolean, TIMESTAMP, TEXT,
    ForeignKey, func, String, JSON, UniqueConstraint,
)
from sqlalchemy.orm import relationship
from app.core.database import Base
from app.models.enums import (
    scenario_category_enum,
    cefr_level_enum,
    progress_status_enum,
)


#  scenarios

class ScenarioDB(Base):
    __tablename__ = "scenarios"

    id              = Column(BigInteger, primary_key=True, autoincrement=True)
    title           = Column(String(255), nullable=False)
    slug            = Column(String(255), unique=True, index=True, nullable=False)
    description     = Column(TEXT, nullable=True)
    category        = Column(scenario_category_enum, nullable=False)
    level           = Column(cefr_level_enum,         nullable=False)
    ai_role         = Column(String(150), nullable=False)
    user_role       = Column(String(150), nullable=False)
    goal_prompt     = Column(TEXT, nullable=False)
    suggested_vocab = Column(JSON, nullable=True)        # ["word1", "word2"]
    order_index     = Column(SmallInteger, default=0, nullable=False)
    is_active       = Column(Boolean, default=True, nullable=False)
    created_at      = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())
    updated_at      = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    roadmap_steps = relationship("RoadmapStepDB", back_populates="scenario")
    chat_sessions = relationship("ChatSessionDB", back_populates="scenario")


#  roadmap_steps

class RoadmapStepDB(Base):
    __tablename__ = "roadmap_steps"

    id               = Column(BigInteger, primary_key=True, autoincrement=True)
    level            = Column(cefr_level_enum, nullable=False)
    week_number      = Column(SmallInteger, nullable=False)
    title            = Column(String(255), nullable=False)
    scenario_id      = Column(BigInteger, ForeignKey("scenarios.id", ondelete="RESTRICT"), nullable=False, index=True)
    unlock_condition = Column(String(255), nullable=True)
    created_at       = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())

    scenario      = relationship("ScenarioDB", back_populates="roadmap_steps")
    user_progress = relationship("UserProgressDB", back_populates="roadmap_step")


#  user_progress

class UserProgressDB(Base):
    __tablename__ = "user_progress"
    __table_args__ = (
        UniqueConstraint("user_id", "roadmap_step_id", name="uq_user_roadmap_step"),
    )

    id              = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id         = Column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    roadmap_step_id = Column(BigInteger, ForeignKey("roadmap_steps.id", ondelete="CASCADE"), nullable=False, index=True)
    status          = Column(progress_status_enum, nullable=False)
    completed_at    = Column(TIMESTAMP(timezone=True), nullable=True)
    created_at      = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())
    updated_at      = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    user         = relationship("UserDB", back_populates="progress")
    roadmap_step = relationship("RoadmapStepDB", back_populates="user_progress")