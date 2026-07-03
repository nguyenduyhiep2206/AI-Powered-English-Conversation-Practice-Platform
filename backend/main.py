import os

from fastapi import FastAPI, status
from app.api import auth, user, google_auth
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

app = FastAPI()

app.include_router(auth.router)
app.include_router(user.router)
app.include_router(google_auth.router)

@app.get("/ping", status_code=status.HTTP_200_OK)
async def ping():
    return {"message": "pong"}

load_dotenv()

FRONTEND_URL = os.getenv("FRONTEND_URL")

origins = [FRONTEND_URL]
 
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True, # cho phép gửi cookie kèm request
    allow_methods=["*"],
    allow_headers=["*"],
)