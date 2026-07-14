import io
import re
import uuid

from fastapi import HTTPException, UploadFile, status
from pypdf import PdfReader
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.book import BookDB
from app.models.enums import BookStatusEnum, BookTypeEnum, CEFRLevel
from app.services import supabase_storage_service

PDF_CONTENT_TYPE = "application/pdf"
MAX_BYTES = settings.MAX_BOOK_UPLOAD_MB * 1024 * 1024


def _safe_filename(name: str) -> str:
    stem = name.rsplit("/", 1)[-1]
    stem = stem[:-4] if stem.lower().endswith(".pdf") else stem
    cleaned = re.sub(r"[^a-zA-Z0-9._-]+", "_", stem).strip("._")
    return cleaned or "book"


def _validate_pdf(content: bytes) -> int:
    try:
        reader = PdfReader(io.BytesIO(content))
        page_count = len(reader.pages)
        if page_count == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="PDF has no readable pages",
            )
        return page_count
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Corrupt or invalid PDF file",
        ) from exc


async def _get_book_or_404(db: AsyncSession, book_id: int) -> BookDB:
    result = await db.execute(select(BookDB).where(BookDB.id == book_id))
    book = result.scalar_one_or_none()
    if book is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Book not found")
    return book


async def list_books(db: AsyncSession) -> list[BookDB]:
    result = await db.execute(select(BookDB).order_by(BookDB.created_at.desc()))
    return list(result.scalars().all())


async def get_book(db: AsyncSession, book_id: int) -> BookDB:
    return await _get_book_or_404(db, book_id)


async def upload_book(
    db: AsyncSession,
    *,
    file: UploadFile,
    title: str,
    description: str | None,
    cefr_level: CEFRLevel | None,
    book_type: BookTypeEnum,
    uploaded_by: int,
) -> BookDB:
    if not supabase_storage_service.is_configured():
        detail = supabase_storage_service.configuration_error() or "Supabase Storage is not configured"
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=detail,
        )

    if file.content_type not in (PDF_CONTENT_TYPE, "application/octet-stream"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only PDF files are allowed",
        )

    original_name = file.filename or "book.pdf"
    if not original_name.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File must have a .pdf extension",
        )

    content = await file.read()
    if not content:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Empty file")
    if len(content) > MAX_BYTES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File exceeds {settings.MAX_BOOK_UPLOAD_MB}MB limit",
        )

    if not content.startswith(b"%PDF"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid PDF file")

    page_count = _validate_pdf(content)

    book = BookDB(
        title=title.strip(),
        description=description.strip() if description else None,
        cefr_level=cefr_level,
        book_type=book_type,
        file_path="",
        file_size=len(content),
        page_count=page_count,
        status=BookStatusEnum.uploaded,
        uploaded_by=uploaded_by,
        chunk_count=0,
    )
    db.add(book)
    await db.flush()

    storage_path = f"{book.id}_{uuid.uuid4().hex}_{_safe_filename(original_name)}.pdf"
    try:
        file_url, stored_path = supabase_storage_service.upload_pdf(content, storage_path)
    except Exception as exc:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to upload to Supabase Storage: {exc}",
        )

    book.file_path = file_url
    book.file_public_id = stored_path

    await db.commit()
    await db.refresh(book)
    return book


async def delete_book(db: AsyncSession, book_id: int) -> tuple[BookDB, int]:
    book = await _get_book_or_404(db, book_id)

    from app.services.book_chunk_service import delete_book_chunks

    deleted_chunks = delete_book_chunks(int(book.id))

    if book.file_public_id:
        try:
            supabase_storage_service.delete_pdf(book.file_public_id)
        except Exception:
            # Best-effort: still remove the DB record even if Supabase delete fails.
            pass

    await db.delete(book)
    await db.commit()
    return book, deleted_chunks
