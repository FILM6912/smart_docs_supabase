from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime

class DocumentBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    category_name: Optional[str] = Field(None, max_length=100)
    data: str

class DocumentCreate(DocumentBase):
    pass

class DocumentUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    category_name: Optional[str] = Field(None, max_length=100)
    data: Optional[str] = None
    last_updated: Optional[datetime] = None
    updated_by: Optional[str] = None

class DocumentResponse(DocumentBase):
    id: int
    created_at: Optional[datetime] = None
    last_updated: Optional[datetime] = None
    updated_by: Optional[str] = None
    created_by: Optional[str] = None
    created_by_id: Optional[str] = None
    updated_by_id: Optional[str] = None

    class Config:
        from_attributes = True

class CategoryBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    department: Optional[str] = Field(None, max_length=100)

class CategoryCreate(CategoryBase):
    pass

class CategoryUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    department: Optional[str] = Field(None, max_length=100)

class CategoryResponse(CategoryBase):
    id: int
    created_at: Optional[datetime] = None
    created_by: Optional[str] = None
    created_by_id: Optional[str] = None
    updated_by: Optional[str] = None
    updated_by_id: Optional[str] = None

    class Config:
        from_attributes = True

# Models for new payload format
class ImageReference(BaseModel):
    refer: str  # ข้อความอ้างอิงรูปภาพใน content เช่น "![รูปภาพ](blob:http://localhost:5173/fd735971-bd60-4232-b96a-37d9d5354a4c)"
    imgByte: str  # ข้อมูลรูปภาพในรูปแบบ base64

class DocumentData(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    content: str  # เนื้อหาที่มีรูปภาพแทรกอยู่ในรูปแบบ markdown
    category: str = Field(..., min_length=1, max_length=100)

class DocumentPayload(BaseModel):
    docData: DocumentData
    imgRef: List[ImageReference] = []  # รายการรูปภาพที่ต้องอัปโหลด