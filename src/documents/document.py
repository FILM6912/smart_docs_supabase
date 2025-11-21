from fastapi import APIRouter, Depends, HTTPException, status, Query
from datetime import datetime
from ..auth.auth_utils import get_current_user, is_admin
from ..database.supabase import supabase
from .model import (
    DocumentCreate,
    DocumentUpdate,
    DocumentResponse,
    CategoryCreate,
    CategoryUpdate,
    CategoryResponse,
    DocumentPayload,
    ImageReference,
)
from .documents_utils import process_document_images, delete_document_images
from .embeding import get_embedding
from typing import List, Dict, Optional

router = APIRouter()
category_router = APIRouter()
public_router = APIRouter()


@router.get("/", response_model=list[DocumentResponse])
async def list_documents(
    q: str | None = Query(None),
    category_name: str | None = Query(None),
    department: str | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    current_user: dict = Depends(get_current_user),
):
    try:
        # ถ้าไม่ได้ส่ง department มา ให้ใช้ department ของ user ปัจจุบัน
        
        if department is None or department == "":
            department = current_user.get("department")
        
        # Debug: แสดงค่า department ที่ได้รับ
        print(f"Debug - department parameter: {department}")
        print(f"Debug - current_user: {current_user}")
        print(f"Debug - current_user.get('department'): {current_user.get('department')}")

        query = supabase.schema("smart_documents").table("documents").select("*")
        if category_name:
            query = query.eq("category_name", category_name)
        # ถ้า department เป็น "*" ให้ดึงทุกแผนก จึงไม่ต้องเพิ่มเงื่อนไข
        if current_user["role"] in ["superadmin"]:
            department="*"

        if current_user["role"] in ["admin","user"] and department == "*":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="ไม่มีสิทธิ์ในการดึงเอกสารทั้งหมด",
            )
        
        if department and department != "*":
            # ดึงข้อมูล categories ที่อยู่ใน department ที่ระบุ
            categories_in_dept = supabase.schema("smart_documents").table("categories").select("name").eq("department", department).execute().data
            category_names = [cat["name"] for cat in categories_in_dept]
            if category_names:
                query = query.in_("category_name", category_names)
            else:
                # ถ้าไม่มี categories ใน department ที่ระบุ ให้คืนค่าว่าง
                return []
        if q:
            query = query.ilike("title", f"%{q}%")

        data = query.range(offset, offset + limit - 1).execute().data
        return [DocumentResponse(**item) for item in data]
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"เกิดข้อผิดพลาดในการดึงข้อมูลเอกสาร: {str(e)}",
        )


@router.get("/{doc_id}", response_model=DocumentResponse)
async def get_document(doc_id: int, current_user: dict = Depends(get_current_user)):
    try:
        data = (
            supabase.schema("smart_documents")
            .table("documents")
            .select("*")
            .eq("id", doc_id)
            .execute()
            .data
        )
        if not data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="ไม่พบเอกสาร"
            )
        return DocumentResponse(**data[0])
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"เกิดข้อผิดพลาดในการดึงเอกสาร: {str(e)}",
        )


@router.post("/", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
async def create_document(
    payload: DocumentPayload, current_user: dict = Depends(is_admin)
):
    try:
        # ดึงข้อมูลจาก payload
        doc_data = payload.docData
        img_refs = payload.imgRef

        # ตรวจสอบว่ามีหมวดหมู่นี้ในระบบหรือไม่
        category_name = doc_data.category
        if category_name:
            cats = (
                supabase.schema("smart_documents")
                .table("categories")
                .select("id")
                .eq("name", category_name)
                .execute()
                .data
            )
            if not cats:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"ไม่พบหมวดหมู่ '{category_name}' ในตาราง categories",
                )

        insert_data = {
            "title": doc_data.title,
            "category_name": doc_data.category,
            "data": "",  # ใช้ content ว่างไปก่อน
            "created_by": current_user["full_name"],
            "created_by_id": current_user["id"],
            "embedding": get_embedding(doc_data.content),
        }

        result = (
            supabase.schema("smart_documents")
            .table("documents")
            .insert(insert_data)
            .execute()
            .data
        )

        # ดึง doc_id ที่เพิ่งสร้าง
        doc_id = result[0]["id"]

        # ประมวลผลรูปภาพและอัปเดต content
        updated_content = process_document_images(doc_data.content, img_refs, doc_id)

        # อัปเดตเอกสารด้วย content ที่มีรูปภาพแล้ว
        update_data = {
            "data": updated_content,
            "embedding": get_embedding(updated_content),
        }

        updated_result = (
            supabase.schema("smart_documents")
            .table("documents")
            .update(update_data)
            .eq("id", doc_id)
            .execute()
            .data
        )

        return DocumentResponse(**updated_result[0])
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"เกิดข้อผิดพลาดในการสร้างเอกสาร: {str(e)}",
        )


@router.put("/{doc_id}", response_model=DocumentResponse)
async def update_document(
    doc_id: int, payload: DocumentPayload, current_user: dict = Depends(is_admin)
):
    try:
        # ตรวจสอบว่ามีเอกสารนี้ในระบบหรือไม่
        existing = (
            supabase.schema("smart_documents")
            .table("documents")
            .select("*")
            .eq("id", doc_id)
            .execute()
            .data
        )
        if not existing:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="ไม่พบเอกสาร"
            )

        # ดึงข้อมูลจาก payload
        doc_data = payload.docData
        img_refs = payload.imgRef

        # ตรวจสอบว่ามีหมวดหมู่นี้ในระบบหรือไม่
        category_name = doc_data.category
        if category_name:
            cats = (
                supabase.schema("smart_documents")
                .table("categories")
                .select("id")
                .eq("name", category_name)
                .execute()
                .data
            )
            if not cats:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"ไม่พบหมวดหมู่ '{category_name}' ในตาราง categories",
                )

        # ประมวลผลรูปภาพและอัปเดต content
        updated_content = process_document_images(doc_data.content, img_refs, doc_id)

        # สร้างข้อมูลสำหรับ update
        update_data = {
            "embedding": get_embedding(updated_content),
            "title": doc_data.title,
            "category_name": doc_data.category,
            "data": updated_content,
            "last_updated": datetime.utcnow().isoformat(),
            "updated_by": current_user["full_name"],
            "updated_by_id": current_user["id"],
        }

        updated = (
            supabase.schema("smart_documents")
            .table("documents")
            .update(update_data)
            .eq("id", doc_id)
            .execute()
            .data
        )

        return DocumentResponse(**updated[0])
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"เกิดข้อผิดพลาดในการอัปเดตเอกสาร: {str(e)}",
        )


@router.delete("/{doc_id}", response_model=dict)
async def delete_document(doc_id: int, current_user: dict = Depends(is_admin)):
    try:
        exists = (
            supabase.schema("smart_documents")
            .table("documents")
            .select("id")
            .eq("id", doc_id)
            .execute()
            .data
        )
        if not exists:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="ไม่พบเอกสาร"
            )

        # ลบรูปภาพที่เกี่ยวข้องกับเอกสาร
        delete_document_images(doc_id)

        supabase.schema("smart_documents").table("documents").delete().eq(
            "id", doc_id
        ).execute()
        return {"message": "ลบเอกสารและรูปภาพที่เกี่ยวข้องสำเร็จ"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"เกิดข้อผิดพลาดในการลบเอกสาร: {str(e)}",
        )


@category_router.get("/", response_model=list[CategoryResponse])
async def list_categories(
    department: str | None = Query(None),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    current_user: dict = Depends(get_current_user),
):
    try:
        query = supabase.schema("smart_documents").table("categories").select("*")

        if current_user["role"] in ["admin","user"] and department == "*":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="ไม่มีสิทธิ์ในการดึงเอกสารทั้งหมด",
            )
        elif current_user["role"] in ["superadmin"]:...
        elif department:
            query = query.eq("department", department)
        else:
            query = query.eq("department", current_user["department"])
        data = query.range(offset, offset + limit - 1).execute().data
        return [CategoryResponse(**item) for item in data]
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"เกิดข้อผิดพลาดในการดึงหมวดหมู่: {str(e)}",
        )


@category_router.get("/{cat_id}", response_model=CategoryResponse)
async def get_category(cat_id: int, current_user: dict = Depends(get_current_user)):
    try:
        data = (
            supabase.schema("smart_documents")
            .table("categories")
            .select("*")
            .eq("id", cat_id)
            .execute()
            .data
        )
        if not data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="ไม่พบหมวดหมู่"
            )
        return CategoryResponse(**data[0])
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"เกิดข้อผิดพลาดในการดึงหมวดหมู่: {str(e)}",
        )


@category_router.post(
    "/", response_model=CategoryResponse, status_code=status.HTTP_201_CREATED
)
async def create_category(
    payload: CategoryCreate, current_user: dict = Depends(is_admin)
):
    try:
        insert_data = payload.model_dump()
        insert_data["created_by"] = current_user["full_name"]
        insert_data["created_by_id"] = current_user["id"]
        result = (
            supabase.schema("smart_documents")
            .table("categories")
            .insert(insert_data)
            .execute()
            .data
        )
        return CategoryResponse(**result[0])
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"เกิดข้อผิดพลาดในการสร้างหมวดหมู่: {str(e)}",
        )


@category_router.put("/{cat_id}", response_model=CategoryResponse)
async def update_category(
    cat_id: int, payload: CategoryUpdate, current_user: dict = Depends(is_admin)
):
    try:
        exists = (
            supabase.schema("smart_documents")
            .table("categories")
            .select("id")
            .eq("id", cat_id)
            .execute()
            .data
        )
        if not exists:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="ไม่พบหมวดหมู่"
            )
        update_data = payload.model_dump(exclude_unset=True)
        update_data["updated_by"] = current_user["full_name"]
        update_data["updated_by_id"] = current_user["id"]
        updated = (
            supabase.schema("smart_documents")
            .table("categories")
            .update(update_data)
            .eq("id", cat_id)
            .execute()
            .data
        )
        return CategoryResponse(**updated[0])
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"เกิดข้อผิดพลาดในการอัปเดตหมวดหมู่: {str(e)}",
        )


@category_router.delete("/{cat_id}", response_model=dict)
async def delete_category(cat_id: int, current_user: dict = Depends(is_admin)):
    try:
        exists = (
            supabase.schema("smart_documents")
            .table("categories")
            .select("id,name")
            .eq("id", cat_id)
            .execute()
            .data
        )

        if not exists:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="ไม่พบหมวดหมู่"
            )

        if (
            supabase.schema("smart_documents")
            .table("documents")
            .select("category_name")
            .eq("category_name", exists[0]["name"])
            .execute()
            .data
        ):
            raise HTTPException(status_code=423, detail="ข้อมูลนี้กำลังถูกใช้งานอยู่ ไม่สามารถลบได้")

        supabase.schema("smart_documents").table("categories").delete().eq(
            "id", cat_id
        ).execute()
        return {"message": "ลบหมวดหมู่สำเร็จ"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"เกิดข้อผิดพลาดในการลบหมวดหมู่: {str(e)}",
        )


@public_router.get("/search")
async def search_documents(
    query: str,
    match_count: int = 5,
    match_threshold: float = 0.5,
    filter_category: Optional[str] = None,
) -> List[Dict]:
    """ค้นหาเอกสารด้วย vector similarity"""
    try:
        # สร้าง embedding จาก query
        query_embedding = get_embedding(query)

        # เรียกใช้ RPC function (ต้องสร้างใน schema smart_document)
        result = (
            supabase.schema("smart_documents")
            .rpc(
                "search_documents",
                {
                    "query_embedding": query_embedding,
                    "match_count": match_count,
                    "match_threshold": match_threshold,
                    "filter_category": filter_category,
                },
            )
            .execute()
        )
        print(result.data)
        if result.data == []:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="ไม่พบเอกสารที่ตรงกับคำค้น",
            )
        data = [
            {
                "title": item["title"],
                "content": item["data"],
                "category": item["category_name"],
                "score": item["similarity"],
            }
            for item in result.data
        ]
        return data

    except HTTPException:
        # ส่งต่อ HTTPException (เช่น 404) โดยไม่แปลงเป็น 500
        raise
    except Exception as e:
        print(f"❌ Error searching documents: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"เกิดข้อผิดพลาดในการค้นหาเอกสาร: {str(e)}",
        )
