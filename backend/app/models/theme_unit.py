from sqlalchemy import (
    BigInteger,
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import relationship

from app.core.database import Base
from app.models.enums import cefr_level_enum


class LearningThemeUnitDB(Base):
    __tablename__ = "learning_theme_units"
    __table_args__ = (
        UniqueConstraint("slug", "cefr_level", name="uq_theme_units_slug_level"),
    )

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    slug = Column(String(120), nullable=False)
    cefr_level = Column(cefr_level_enum, nullable=False, index=True)
    title = Column(String(500), nullable=False)
    can_do = Column(Text, nullable=False)
    sort_order = Column(Integer, nullable=False, server_default="0")
    is_active = Column(Boolean, nullable=False, server_default="true")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    skills = relationship("ThemeUnitSkillDB", back_populates="theme_unit")


class ThemeUnitSkillDB(Base):
    __tablename__ = "theme_unit_skills"
    __table_args__ = (
        UniqueConstraint("theme_unit_id", "skill_id", name="uq_theme_unit_skill"),
        UniqueConstraint("skill_id", name="uq_theme_unit_skills_skill_id"),
    )

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    theme_unit_id = Column(
        BigInteger,
        ForeignKey("learning_theme_units.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    skill_id = Column(
        BigInteger,
        ForeignKey("learning_skills.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    position = Column(Integer, nullable=False, server_default="0")

    theme_unit = relationship("LearningThemeUnitDB", back_populates="skills")
