from sqlalchemy import (
    BigInteger,
    Column,
    Float,
    ForeignKey,
    Integer,
    TIMESTAMP,
    UniqueConstraint,
    func,
)

from app.core.database import Base


class UserSkillMasteryDB(Base):
    __tablename__ = "user_skill_mastery"
    __table_args__ = (
        UniqueConstraint("user_id", "skill_id", name="uq_user_skill_mastery"),
    )

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    skill_id = Column(
        BigInteger,
        ForeignKey("learning_skills.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    mastery = Column(Float, nullable=False, server_default="0")
    attempts = Column(Integer, nullable=False, server_default="0")
    correct = Column(Integer, nullable=False, server_default="0")
    updated_at = Column(
        TIMESTAMP(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )
