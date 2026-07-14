from sqlalchemy import (
    BigInteger,
    Boolean,
    Column,
    ForeignKey,
    String,
    TIMESTAMP,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import relationship

from app.core.database import Base


class BookSkillSourceDB(Base):
    """Maps one book unit to a canonical learning skill (source provenance)."""

    __tablename__ = "book_skill_sources"
    __table_args__ = (
        UniqueConstraint("book_id", "unit_id", name="uq_book_skill_source_unit"),
    )

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    skill_id = Column(
        BigInteger,
        ForeignKey("learning_skills.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    book_id = Column(BigInteger, ForeignKey("books.id", ondelete="CASCADE"), nullable=False, index=True)
    unit_id = Column(
        BigInteger,
        ForeignKey("book_structure_preview.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    unit_title = Column(String(500), nullable=False)
    section_title = Column(String(255), nullable=True)
    is_excluded = Column(Boolean, nullable=False, server_default="false")
    is_primary = Column(Boolean, nullable=False, server_default="false")
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())

    skill = relationship("LearningSkillDB", back_populates="sources")
