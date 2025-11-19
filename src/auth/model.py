from pydantic import BaseModel, EmailStr, Field
from typing import Optional, Literal
from enum import Enum

class UserRole(str, Enum):
    USER = "user"
    ADMIN = "admin"
    SUPERADMIN = "superadmin"

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserCreate(BaseModel):
    email: EmailStr
    full_name: str = Field(..., min_length=1, max_length=100)
    password: str = Field(..., min_length=8)

class UserResponse(BaseModel):
    id: str
    email: str
    full_name: Optional[str] = None
    role: UserRole = UserRole.USER
    
    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str
    id: str
    email: str
    full_name: str
    role: UserRole
    department: Optional[str] = None

class TokenData(BaseModel):
    id: Optional[str] = None
    email: Optional[str] = None
    role: Optional[UserRole] = None
    full_name: Optional[str] = None
