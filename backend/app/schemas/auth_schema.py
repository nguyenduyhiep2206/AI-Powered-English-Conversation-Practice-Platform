from pydantic import BaseModel
from typing import Optional

class Token(BaseModel):
    access_token: str
    refresh_token: Optional[str] = None
    token_type: str

class Token_data(BaseModel):
    user_id: Optional[str] = None

class RefreshRequest(BaseModel):
    refresh_token: str

class LoginRequest(BaseModel):
    identifier: str
    password: str

class GoogleLoginRequest(BaseModel):
    credential: str # ID token received from Google Sign-In