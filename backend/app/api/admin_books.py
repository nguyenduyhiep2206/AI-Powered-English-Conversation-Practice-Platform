from typing import Optional

from fastapi import APIRouter, Depends, File, Form, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_active_user, require_permission
from app.core.database import get_db
from app.models.enums import BookTypeEnum, CEFRLevel
from app.models.user import UserDB
from app.schemas.book_schema import (
    BookAdmin,
    BookDeleteData,
    BookDeleteResponse,
    BookListResponse,
    BookResponse,
)
from app.services.book_service import delete_book, get_book, list_books, upload_book

router = APIRouter()


def _to_admin(book) -> BookAdmin:
    return BookAdmin.model_validate(book)


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
