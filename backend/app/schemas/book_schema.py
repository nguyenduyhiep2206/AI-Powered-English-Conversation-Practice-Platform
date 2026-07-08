from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from app.models.enums import BookStatusEnum, CEFRLevel


class BookAdmin(BaseModel):
    id: int
    title: str
    description: Optional[str] = None
    cefr_level: Optional[CEFRLevel] = None
    file_path: str
    file_public_id: Optional[str] = None
    file_size: int
    page_count: Optional[int] = None
    status: BookStatusEnum
    uploaded_by: Optional[int] = None
    chunk_count: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class BookListResponse(BaseModel):
    success: bool = True
    data: list[BookAdmin]


class BookResponse(BaseModel):
    success: bool = True
    data: BookAdmin


class BookDeleteData(BaseModel):
    id: int
    deleted_chunks: int = 0
    message: str = "Book deleted successfully"


class BookDeleteResponse(BaseModel):
    success: bool = True
    data: BookDeleteData


class BookUploadForm(BaseModel):
    """Documented fields for multipart upload (actual binding uses Form())."""

    title: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=2000)
    cefr_level: Optional[CEFRLevel] = None
