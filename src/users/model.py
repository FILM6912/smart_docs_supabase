from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import datetime
from ..auth.model import UserRole

class UserBase(BaseModel):
    full_name: str = Field(..., min_length=1, max_length=100)
    department: Optional[str] = Field(None, max_length=100)
    level: Optional[str] = Field(None, max_length=50)
    email: EmailStr
    image_profile: Optional[str] = Field(None, max_length=255)
    role: UserRole = UserRole.USER
    is_active: bool = True

class UserCreate(UserBase):
    password: str = Field(..., min_length=8)

class UserUpdate(BaseModel):
    full_name: Optional[str] = Field(None, min_length=1, max_length=100)
    department: Optional[str] = Field(None, max_length=100)
    level: Optional[str] = Field(None, max_length=50)
    email: Optional[EmailStr] = None
    image_profile: Optional[str] = Field(None, max_length=255)
    role: Optional[UserRole] = None
    is_active: Optional[bool] = None
    password: Optional[str] = Field(None, min_length=8)

class UserResponse(UserBase):
    id: str
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True

class UserInDB(UserBase):
    id: str
    password: str
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True