from contextlib import asynccontextmanager

from fastapi import FastAPI, status
from fastapi.middleware.cors import CORSMiddleware

from app.api import (
    auth,
    user,
    onboarding,
    admin_survey,
    admin_books,
    admin_quiz,
    admin_lessons,
    admin_skills,
    quiz,
    roadmap,
    skills,
    tutor,
)
from app.core.config import settings
from app.core.mongodb import connect_mongo, disconnect_mongo


@asynccontextmanager
async def lifespan(app: FastAPI):
    await connect_mongo()
    try:
        from app.services.book_chunk_service import ensure_book_chunks_indexes_async

        await ensure_book_chunks_indexes_async()
    except Exception:
        pass
    yield
    await disconnect_mongo()


app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.FRONTEND_URL],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api/v1/auth", tags=["auth"])
app.include_router(user.router, prefix="/api/v1", tags=["users"])
app.include_router(onboarding.router, prefix="/api/v1/onboarding", tags=["onboarding"])
app.include_router(admin_survey.router, prefix="/api/v1/admin/survey", tags=["admin-survey"])
app.include_router(admin_books.router, prefix="/api/v1/admin/books", tags=["admin-books"])
app.include_router(admin_quiz.router, prefix="/api/v1/admin/quiz", tags=["admin-quiz"])
app.include_router(admin_lessons.router, prefix="/api/v1/admin/lessons", tags=["admin-lessons"])
app.include_router(admin_skills.router, prefix="/api/v1/admin/skills", tags=["admin-skills"])
app.include_router(quiz.router, prefix="/api/v1/quiz", tags=["quiz"])
app.include_router(skills.router, prefix="/api/v1/skills", tags=["skills"])
app.include_router(roadmap.router, prefix="/api/v1/roadmap", tags=["roadmap"])
app.include_router(tutor.router, prefix="/api/v1/tutor", tags=["tutor"])


@app.get("/ping", status_code=status.HTTP_200_OK)
async def ping():
    return {"message": "pong"}