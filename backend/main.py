from fastapi import FastAPI, status
from fastapi.middleware.cors import CORSMiddleware
from app.api import auth, user, google_auth
from app.core.config import settings

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.FRONTEND_URL],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api/v1/auth", tags=["auth"])
app.include_router(google_auth.router, prefix="/api/v1/auth", tags=["auth"])
app.include_router(user.router, prefix="/api/v1", tags=["users"])


@app.get("/ping", status_code=status.HTTP_200_OK)
async def ping():
    return {"message": "pong"}