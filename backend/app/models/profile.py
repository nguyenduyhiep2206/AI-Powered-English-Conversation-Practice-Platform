from sqlalchemy import (
    Column, BigInteger, SmallInteger, Boolean, TIMESTAMP,
    ForeignKey, func, String,
)
from sqlalchemy.orm import relationship
from app.core.database import Base
from app.models.enums import (
    goal_enum,
    weak_point_enum,
    cefr_level_enum,
)


class UserProfileDB(Base):
    __tablename__ = "user_profiles"

    id               = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id          = Column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True)
    occupation       = Column(String(100), nullable=True)
    goal             = Column(goal_enum, nullable=False)
    weak_point       = Column(weak_point_enum, nullable=True)
    daily_time_min   = Column(SmallInteger, default=30, nullable=False)
    current_level    = Column(cefr_level_enum, nullable=False)
    placement_score  = Column(SmallInteger, nullable=True)
    survey_done      = Column(Boolean, default=False, nullable=False)
    created_at       = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())
    updated_at       = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    user = relationship("UserDB", back_populates="profile")