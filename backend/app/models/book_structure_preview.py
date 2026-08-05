from sqlalchemy import (
    BigInteger,
    Column,
    Float,
    ForeignKey,
    Integer,
    String,
    TIMESTAMP,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship

from app.core.database import Base


class BookStructurePreviewDB(Base):
    __tablename__ = "book_structure_preview"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    book_id = Column(BigInteger, ForeignKey("books.id", ondelete="CASCADE"), nullable=False)
    unit_index = Column(Integer, nullable=False)
    title = Column(String(500), nullable=False)
    page_start = Column(Integer, nullable=False)
    page_end = Column(Integer, nullable=False)
    detection_method = Column(String(50), nullable=False)
    confidence = Column(Float, nullable=False)
    depth_or_source = Column(String(100), nullable=True)
    language_focus = Column(String(1000), nullable=True)
    grammar_cues = Column(JSONB, nullable=True)
    vocab_cues = Column(JSONB, nullable=True)
    content_summary = Column(String(2000), nullable=True)
    enrichment_status = Column(String(20), nullable=True)
    enriched_at = Column(TIMESTAMP(timezone=True), nullable=True)
    enrichment_source = Column(String(20), nullable=True)
    enrichment_method = Column(String(32), nullable=True)
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())

    book = relationship("BookDB", back_populates="structure_preview")
