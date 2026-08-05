from sqlalchemy import (
    BigInteger,
    Boolean,
    Column,
    ForeignKey,
    SmallInteger,
    String,
    TIMESTAMP,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import relationship

from app.core.database import Base
from app.models.enums import cefr_level_enum, skill_type_enum


class LearningSkillDB(Base):
    __tablename__ = "learning_skills"
    __table_args__ = (
        UniqueConstraint("slug", "cefr_level", name="uq_learning_skill_slug_cefr"),
    )

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    slug = Column(String(120), nullable=False, index=True)
    title = Column(String(500), nullable=False)
    cefr_level = Column(cefr_level_enum, nullable=False, index=True)
    skill_type = Column(skill_type_enum, nullable=False, server_default="grammar")
    difficulty_in_level = Column(SmallInteger, nullable=True)
    is_active = Column(Boolean, nullable=False, server_default="true")
    origin = Column(String(20), nullable=False, server_default="legacy")
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())

    sources = relationship("BookSkillSourceDB", back_populates="skill")


class SkillEdgeDB(Base):
    __tablename__ = "skill_edges"
    __table_args__ = (
        UniqueConstraint("from_skill_id", "to_skill_id", name="uq_skill_edge"),
    )

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    from_skill_id = Column(
        BigInteger, ForeignKey("learning_skills.id", ondelete="CASCADE"), nullable=False
    )
    to_skill_id = Column(
        BigInteger, ForeignKey("learning_skills.id", ondelete="CASCADE"), nullable=False
    )
    relation = Column(String(50), nullable=False, server_default="prerequisite")
