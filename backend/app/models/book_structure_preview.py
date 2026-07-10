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
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())

    book = relationship("BookDB", back_populates="structure_preview")
