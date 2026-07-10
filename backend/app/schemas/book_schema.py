from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from app.models.enums import BookStatusEnum, BookTypeEnum, CEFRLevel


class BookAdmin(BaseModel):
    id: int
    title: str
    description: Optional[str] = None
    cefr_level: Optional[CEFRLevel] = None
    book_type: BookTypeEnum
    detection_method: Optional[str] = None
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
    book_type: BookTypeEnum


class StructureUnitPreview(BaseModel):
    unit_index: int
    title: str
    page_start: int
    page_end: int
    detection_method: str
    confidence: float
    depth_or_source: Optional[str] = None

    model_config = {"from_attributes": True}


class StructurePreviewData(BaseModel):
    book_id: int
    detection_method: Optional[str] = None
    confidence: Optional[float] = None
    status: BookStatusEnum
    units: list[StructureUnitPreview]


class StructurePreviewResponse(BaseModel):
    success: bool = True
    data: StructurePreviewData
