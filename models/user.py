from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime

class UserCreate(BaseModel):
    email: EmailStr
    password: str
    name: str

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class GoogleLogin(BaseModel):
    token: str

class UserResponse(BaseModel):
    id: str
    email: EmailStr
    name: str
    created_at: datetime
    
    model_config = {
        "from_attributes": True
    }