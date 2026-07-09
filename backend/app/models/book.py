from sqlalchemy import (
    BigInteger,
    Column,
    ForeignKey,
    Integer,
    String,
    TIMESTAMP,
    func,
)
from sqlalchemy.orm import relationship

from app.core.database import Base
from app.models.enums import book_status_enum, book_type_enum, cefr_level_enum


class BookDB(Base):
    __tablename__ = "books"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    title = Column(String(255), nullable=False)
    description = Column(String(2000), nullable=True)
    cefr_level = Column(cefr_level_enum, nullable=True)
    book_type = Column(book_type_enum, nullable=False, server_default="freeform")
    detection_method = Column(String(50), nullable=True)
    file_path = Column(String(500), nullable=False)
    file_public_id = Column(String(500), nullable=True)
    file_size = Column(BigInteger, nullable=False)
    page_count = Column(Integer, nullable=True)
    status = Column(book_status_enum, nullable=False, server_default="uploaded")
    uploaded_by = Column(BigInteger, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    chunk_count = Column(Integer, nullable=False, server_default="0")
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(
        TIMESTAMP(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    uploader = relationship("UserDB", foreign_keys=[uploaded_by])
