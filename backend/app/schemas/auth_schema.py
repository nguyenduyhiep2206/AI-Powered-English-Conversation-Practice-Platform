from pydantic import BaseModel
from typing import Optional

class Token(BaseModel):
    access_token: str
    token_type: str

class Token_data(BaseModel):
    user_id: Optional[str] = None

class LoginRequest(BaseModel):
    identifier: str
    password: str

class GoogleLoginRequest(BaseModel):
    credential: str # ID token received from Google Sign-In


class MeData(BaseModel):
    id: int
    username: str
    email: str
    full_name: Optional[str] = None
    avatar_url: Optional[str] = None
    is_active: bool
    auth_provider: str
    roles: list[str]
    permissions: list[str]


class MeResponse(BaseModel):
    success: bool
    data: MeData