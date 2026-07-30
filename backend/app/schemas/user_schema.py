from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

class User(BaseModel):
    username: str
    email: Optional[str] = None
    full_name: Optional[str] = None
    avatar_url: Optional[str] = None
    auth_provider: str = "local"

class UserCreate(User):
    password: str = Field(..., min_length=8, description="Password must be at least 8 characters long")

class UpdateUser(BaseModel):
    username: Optional[str]
    full_name: Optional[str] = Field(None, max_length=100)
    avatar_url: Optional[str] = None
    is_active: Optional[bool] = None
    updated_at: Optional[datetime] = None
    
class UserResponse(User):
    id: int
    is_active: bool
    created_at: datetime  
    updated_at: datetime

    model_config = {
        "from_attributes": True
    }

class UserinDB(User):
    hashed_password: str