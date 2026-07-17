from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_active_user, require_permission
from app.core.database import get_db
from app.models.enums import BookStatusEnum, BookTypeEnum, CEFRLevel
from app.models.user import UserDB
from app.schemas.book_schema import (
    BookAdmin,
    BookDeleteData,
    BookDeleteResponse,
    BookListResponse,
    BookResponse,
    StructurePreviewData,
    StructurePreviewResponse,
    StructureUnitPreview,
)
from app.services.book_indexing_service import (
    confirm_and_start_indexing,
    index_book,
    reindex_unit,
    retry_embeddings,
)
from app.services.book_service import delete_book, get_book, list_books, upload_book
from app.services.book_structure_service import (
    detect_book_structure,
    detect_book_structure_job,
    get_structure_preview,
)

router = APIRouter()


def _to_admin(book) -> BookAdmin:
    return BookAdmin.model_validate(book)


def _to_structure_preview(summary) -> StructurePreviewData:
    return StructurePreviewData(
        book_id=summary.book_id,
        detection_method=summary.detection_method,
        confidence=summary.confidence,
        status=summary.status,
        units=[StructureUnitPreview.model_validate(unit) for unit in summary.units],
    )


@router.get(
    "",
    response_model=BookListResponse,
    dependencies=[Depends(require_permission("book:manage"))],
)
async def admin_list_books(db: AsyncSession = Depends(get_db)):
    books = await list_books(db)
    return BookListResponse(data=[_to_admin(book) for book in books])


@router.get(
    "/{book_id}",
    response_model=BookResponse,
    dependencies=[Depends(require_permission("book:manage"))],
)
async def admin_get_book(book_id: int, db: AsyncSession = Depends(get_db)):
    book = await get_book(db, book_id)
    return BookResponse(data=_to_admin(book))


@router.post(
    "/upload",
    response_model=BookResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("book:manage"))],
)
async def admin_upload_book(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    title: str = Form(...),
    description: Optional[str] = Form(None),
    cefr_level: Optional[CEFRLevel] = Form(None),
    book_type: BookTypeEnum = Form(...),
    db: AsyncSession = Depends(get_db),
    current_user: UserDB = Depends(get_current_active_user),
):
    book = await upload_book(
        db,
        file=file,
        title=title,
        description=description,
        cefr_level=cefr_level,
        book_type=book_type,
        uploaded_by=int(current_user.id),
    )
    background_tasks.add_task(detect_book_structure_job, int(book.id))
    return BookResponse(data=_to_admin(book))


@router.delete(
    "/{book_id}",
    response_model=BookDeleteResponse,
    dependencies=[Depends(require_permission("book:manage"))],
)
async def admin_delete_book(book_id: int, db: AsyncSession = Depends(get_db)):
    book, deleted_chunks = await delete_book(db, book_id)
    return BookDeleteResponse(
        data=BookDeleteData(
            id=int(book.id),
            deleted_chunks=deleted_chunks,
            message="Book deleted successfully",
        )
    )


@router.post(
    "/{book_id}/detect-structure",
    response_model=StructurePreviewResponse,
    dependencies=[Depends(require_permission("book:manage"))],
)
async def admin_detect_book_structure(
    book_id: int,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    outcome = await detect_book_structure(db, book_id)
    if outcome.should_index:
        background_tasks.add_task(index_book, book_id)
    return StructurePreviewResponse(data=_to_structure_preview(outcome.summary))


@router.get(
    "/{book_id}/structure-preview",
    response_model=StructurePreviewResponse,
    dependencies=[Depends(require_permission("book:manage"))],
)
async def admin_get_structure_preview(book_id: int, db: AsyncSession = Depends(get_db)):
    summary = await get_structure_preview(db, book_id)
    return StructurePreviewResponse(data=_to_structure_preview(summary))


@router.post(
    "/{book_id}/confirm-and-index",
    response_model=BookResponse,
    dependencies=[Depends(require_permission("book:manage"))],
)
async def admin_confirm_and_index(
    book_id: int,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """Confirm structure preview and start two-phase indexing in the background.

    Phase 1: chunk text → Mongo (no Voyage). Phase 2: embed pending chunks.
    TODO: for large books, move off FastAPI BackgroundTasks to Celery/ARQ.
    """
    book = await confirm_and_start_indexing(db, book_id)
    background_tasks.add_task(index_book, book_id)
    return BookResponse(data=_to_admin(book))


@router.post(
    "/{book_id}/reindex-unit/{unit_id}",
    response_model=BookResponse,
    dependencies=[Depends(require_permission("book:manage"))],
)
async def admin_reindex_unit(
    book_id: int,
    unit_id: int,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """Re-chunk a single unit (phase 1), then best-effort embed (phase 2)."""
    book = await get_book(db, book_id)
    book.status = BookStatusEnum.processing
    await db.commit()
    await db.refresh(book)
    background_tasks.add_task(reindex_unit, book_id, unit_id)
    return BookResponse(data=_to_admin(book))


@router.post(
    "/{book_id}/retry-embeddings",
    response_model=BookResponse,
    dependencies=[Depends(require_permission("book:manage"))],
)
async def admin_retry_embeddings(
    book_id: int,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """Resume Voyage embeddings for pending/failed chunks without re-chunking PDF."""
    book = await get_book(db, book_id)
    background_tasks.add_task(retry_embeddings, book_id)
    return BookResponse(data=_to_admin(book))
