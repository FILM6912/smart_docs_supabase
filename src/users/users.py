from fastapi import APIRouter, Depends, HTTPException, status, File, UploadFile, Form
from fastapi.security import OAuth2PasswordRequestForm
from datetime import timedelta
from ..auth.auth_utils import (
    create_access_token,
    get_password_hash,
    get_current_user,
    is_user,
    is_admin,
    is_superadmin,
)
from ..database import supabase, upload_profile_image, delete_user_profile_image
from .model import UserCreate, UserUpdate, UserResponse
import os
from dotenv import load_dotenv
import base64
import uuid
import re

load_dotenv()

ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES"))

router = APIRouter()


@router.get("/me", response_model=UserResponse)
async def get_current_user_profile(current_user: dict = Depends(get_current_user)):
    """ดึงข้อมูลโปรไฟล์ผู้ใช้ปัจจุบัน"""
    current_user = (
        supabase.schema("smart_documents")
        .table("users")
        .select("*")
        .eq("id", current_user["id"])
        .execute()
        .data[0]
    )
    return UserResponse(
        id=current_user["id"],
        email=current_user["email"],
        full_name=current_user["full_name"],
        image_profile=current_user.get("image_profile"),
        created_at=current_user.get("created_at"),
        updated_at=current_user.get("updated_at"),
        is_active=current_user.get("is_active", True),
        role=current_user["role"],
        department=current_user.get("department"),
        level=current_user.get("level"),
    )


@router.get("/{user_id_or_email}", response_model=UserResponse)
async def get_user_profile(
    user_id_or_email: str, current_user: dict = Depends(is_user)
):
    """ดึงข้อมูลโปรไฟล์ผู้ใช้ตาม ID หรือ Email"""
    # ตรวจสอบว่าเป็น email หรือ ID
    email_pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    is_email = re.match(email_pattern, user_id_or_email) is not None

    try:
        if is_email:
            # ค้นหาตาม email
            user_data = (
                supabase.schema("smart_documents")
                .table("users")
                .select("*")
                .eq("email", user_id_or_email)
                .execute()
                .data
            )
        else:
            # ค้นหาตาม ID
            user_data = (
                supabase.schema("smart_documents")
                .table("users")
                .select("*")
                .eq("id", user_id_or_email)
                .execute()
                .data
            )

        if not user_data:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="ไม่พบผู้ใช้")

        user = user_data[0]
        print(user)
        return UserResponse(
            id=user["id"],
            email=user["email"],
            full_name=user["full_name"],
            department=user.get("department"),
            level=user.get("level"),
            image_profile=user.get("image_profile"),
            role=user["role"],
            is_active=user.get("is_active", True),
            created_at=user.get("created_at"),
            updated_at=user.get("updated_at"),
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"เกิดข้อผิดพลาดในการดึงข้อมูลผู้ใช้: {str(e)}",
        )


@router.put("/{user_id_or_email}", response_model=UserResponse)
async def update_user_profile(
    user_id_or_email: str,
    image_profile: UploadFile = File(None),
    full_name: str = Form(""),
    department: str = Form(""),
    level: str = Form(""),
    email: str = Form(""),
    role: str = Form(""),
    is_active: bool = Form(None),
    password: str = Form(""),
    current_user: dict = Depends(get_current_user),
):
    """อัปเดตข้อมูลโปรไฟล์ผู้ใช้โดยใช้ form data และไฟล์"""
    # Convert empty strings to None for proper handling
    if full_name == "":
        full_name = None
    if department == "":
        department = None
    if level == "":
        level = None
    if email == "":
        email = None
    if role == "":
        role = None
    if password == "":
        password = None
    # ตรวจสอบว่าเป็น email หรือ ID
    email_pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    is_email = re.match(email_pattern, user_id_or_email) is not None

    try:
        if is_email:
            # ค้นหาตาม email
            user_data = (
                supabase.schema("smart_documents")
                .table("users")
                .select("*")
                .eq("email", user_id_or_email)
                .execute()
                .data
            )
        else:
            # ค้นหาตาม ID
            user_data = (
                supabase.schema("smart_documents")
                .table("users")
                .select("*")
                .eq("id", user_id_or_email)
                .execute()
                .data
            )

        if not user_data:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="ไม่พบผู้ใช้")

        user = user_data[0]
        user_id = user["id"]

        if current_user["role"] == "user" and (user["role"] in ["admin", "superadmin"]):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="ไม่มีสิทธิ์ในการอัปเดตโปรไฟล์นี้"
            )
        elif current_user["role"] == "admin" and user["role"] == "superadmin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="ไม่มีสิทธิ์ในการอัปเดตโปรไฟล์นี้"
            )
        elif current_user["id"] != user["id"] and current_user["role"] != "superadmin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="ไม่มีสิทธิ์ในการอัปเดตโปรไฟล์นี้"
            )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"เกิดข้อผิดพลาดในการค้นหาผู้ใช้: {str(e)}",
        )

    # ตรวจสอบสิทธิ์: admin หรือ superadmin สามารถอัปเดตได้ทุกคน ผู้ใช้ธรรมดาสามารถอัปเดตได้แค่ตัวเอง
    if (
        current_user["role"] not in ["admin", "superadmin"]
        and current_user["id"] != user_id
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="ไม่มีสิทธิ์ในการอัปเดตโปรไฟล์นี้"
        )

    # สร้างข้อมูลที่จะอัปเดต
    update_data = {}

    # เพิ่มข้อมูลที่ไม่ใช่ None และไม่ใช่ empty string
    if full_name is not None and full_name != "":
        update_data["full_name"] = full_name
    if department is not None and department != "":
        update_data["department"] = department
    if level is not None and level != "":
        update_data["level"] = level
    if email is not None and email != "":
        update_data["email"] = email
    if role is not None and role != "":
        update_data["role"] = role
    if is_active is not None:
        update_data["is_active"] = is_active
    if password is not None and password != "":
        update_data["password"] = get_password_hash(password)

    # ถ้ามีการอัปโหลดรูปภาพ
    if image_profile is not None and image_profile.filename != "":
        # ตรวจสอบประเภทไฟล์
        if not image_profile.content_type or not image_profile.content_type.startswith(
            "image/"
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="กรุณาอัปโหลดไฟล์รูปภาพเท่านั้น",
            )

        # อ่านข้อมูลไฟล์และแปลงเป็น base64
        file_content = await image_profile.read()
        base64_image = base64.b64encode(file_content).decode("utf-8")

        # อัปโหลดรูปภาพ
        try:
            image_result = upload_profile_image(user_id, base64_image)
            update_data["image_profile"] = image_result["url"]
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"เกิดข้อผิดพลาดในการอัปโหลดรูปภาพ: {str(e)}",
            )

    # อัปเดตข้อมูลในฐานข้อมูล
    if update_data:
        try:
            updated_user = (
                supabase.schema("smart_documents")
                .table("users")
                .update(update_data)
                .eq("id", user_id)
                .execute()
                .data[0]
            )
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"เกิดข้อผิดพลาดในการอัปเดตข้อมูล: {str(e)}",
            )
    else:
        # ถ้าไม่มีข้อมูลที่จะอัปเดต ให้ดึงข้อมูลปัจจุบัน
        try:
            updated_user = (
                supabase.schema("smart_documents")
                .table("users")
                .select("*")
                .eq("id", user_id)
                .execute()
                .data[0]
            )
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"ไม่สามารถดึงข้อมูลผู้ใช้: {str(e)}",
            )

    return UserResponse(
        id=updated_user["id"],
        email=updated_user["email"],
        full_name=updated_user["full_name"],
        department=updated_user.get("department"),
        level=updated_user.get("level"),
        image_profile=updated_user.get("image_profile"),
        role=updated_user["role"],
        is_active=updated_user.get("is_active", None),
        created_at= updated_user.get("created_at", True),
        updated_at= updated_user.get("updated_at", True),
    )


@router.post("/upload-profile-image-file", response_model=dict)
async def upload_profile_image_file(
    file: UploadFile = File(...), current_user: dict = Depends(get_current_user)
):
    """
    อัปโหลดรูปโปรไฟล์ผู้ใช้จากไฟล์

    **Parameters:**
    - file: ไฟล์รูปภาพ (JPEG, PNG, etc.)

    **Usage:**
    POST /users/upload-profile-image-file
    Body: form-data with key 'file' containing image file
    """
    try:
        # ตรวจสอบประเภทไฟล์
        if not file.content_type or not file.content_type.startswith("image/"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="กรุณาอัปโหลดไฟล์รูปภาพเท่านั้น",
            )

        # อ่านข้อมูลไฟล์และแปลงเป็น base64
        file_content = await file.read()
        base64_image = base64.b64encode(file_content).decode("utf-8")

        # อัปโหลดรูปภาพ
        result = upload_profile_image(current_user["id"], base64_image)

        return {
            "message": "อัปโหลดรูปโปรไฟล์สำเร็จ",
            "image_url": result["url"],
            "user": {
                "id": result["user"]["id"],
                "email": result["user"]["email"],
                "full_name": result["user"]["full_name"],
                "image_profile": result["user"]["image_profile"],
            },
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"เกิดข้อผิดพลาดในการอัปโหลดรูปภาพ: {str(e)}",
        )


@router.delete("/profile-image", response_model=dict)
async def delete_profile_image(
    current_user: dict = Depends(get_current_user)
):
    """
    ลบรูปโปรไฟล์ของผู้ใช้ปัจจุบัน
    
    **Usage:**
    DELETE /users/profile-image
    """
    try:
        # ตรวจสอบว่าผู้ใช้มีรูปโปรไฟล์หรือไม่
        user_data = supabase.schema("smart_documents").table("users").select("image_profile").eq("id", current_user["id"]).execute().data
        if not user_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="ไม่พบข้อมูลผู้ใช้"
            )
        
        image_url = user_data[0].get("image_profile")
        print(f"รูปโปรไฟล์ปัจจุบัน: {image_url}")
        
        if not image_url:
            return {
                "message": "ไม่มีรูปโปรไฟล์ให้ลบ",
                "user": {
                    "id": current_user["id"],
                    "email": current_user["email"],
                    "full_name": current_user["full_name"],
                    "image_profile": None
                }
            }
        
        # ลบรูปโปรไฟล์จาก Supabase Storage
        print(f"กำลังลบรูปโปรไฟล์ของผู้ใช้: {current_user['id']}")
        delete_result = delete_user_profile_image(current_user["id"])
        print(f"ผลลัพธ์จากการลบรูป: {delete_result}")
        
        if not delete_result.get("success", False):
            print(f"การลบรูปล้มเหลว: {delete_result.get('message', 'ไม่สามารถลบรูปโปรไฟล์ได้')}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=delete_result.get("message", "ไม่สามารถลบรูปโปรไฟล์ได้")
            )
        
        # อัปเดตฐานข้อมูลให้ image_profile เป็น null
        supabase.schema("smart_documents").table("users").update({"image_profile": None}).eq("id", current_user["id"]).execute()
        
        return {
            "message": "ลบรูปโปรไฟล์สำเร็จ",
            "user": {
                "id": current_user["id"],
                "email": current_user["email"],
                "full_name": current_user["full_name"],
                "image_profile": None
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"เกิดข้อผิดพลาดในการลบรูปโปรไฟล์: {str(e)}"
        )


@router.delete("/{user_id_or_email}", response_model=dict)
async def delete_user(
    user_id_or_email: str, current_user: dict = Depends(get_current_user)
):
    """ลบผู้ใช้"""
    # ตรวจสอบว่าเป็น email หรือ ID
    email_pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    is_email = re.match(email_pattern, user_id_or_email) is not None

    try:
        if is_email:
            # ค้นหาตาม email
            user_data = (
                supabase.schema("smart_documents")
                .table("users")
                .select("*")
                .eq("email", user_id_or_email)
                .execute()
                .data
            )
        else:
            # ค้นหาตาม ID
            user_data = (
                supabase.schema("smart_documents")
                .table("users")
                .select("*")
                .eq("id", user_id_or_email)
                .execute()
                .data
            )

        if not user_data:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="ไม่พบผู้ใช้")

        user = user_data[0]
        user_id = user["id"]

        if current_user["role"] == "user" and (user["role"] in ["admin", "superadmin"]):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="ไม่มีสิทธิ์ในการอัปเดตโปรไฟล์นี้"
            )
        elif current_user["role"] == "admin" and user["role"] == "superadmin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="ไม่มีสิทธิ์ในการอัปเดตโปรไฟล์นี้"
            )
        elif current_user["id"] != user["id"] and current_user["role"] == "user":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="ไม่มีสิทธิ์ในการลบผู้ใช้นี้"
            )
        

        # ลบรูปโปรไฟล์จาก Supabase Storage (ถ้ามี)
        delete_result = delete_user_profile_image(user_id)
        if not delete_result.get("success", False):
            # แสดงคำเตือนแต่ยังคงลบผู้ใช้ต่อไป
            print(f"คำเตือน: {delete_result.get('message', 'ไม่สามารถลบรูปโปรไฟล์')}")

        # ลบผู้ใช้จากฐานข้อมูล
        supabase.schema("smart_documents").table("users").delete().eq(
            "id", user_id
        ).execute()

        return {"message": f"ลบผู้ใช้ {user_id_or_email} เรียบร้อยแล้ว"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"เกิดข้อผิดพลาดในการลบผู้ใช้: {str(e)}",
        )

@router.get("/", response_model=list[UserResponse])
async def get_all_users(
    current_user: dict = Depends(is_admin)
):
    """ดึงข้อมูลผู้ใช้ทั้งหมด (เฉพาะ admin และ superadmin)"""
    try:
        users = (
            supabase.schema("smart_documents")
            .table("users")
            .select("*")
            .execute()
            .data
        )
        if not users:
            return []

        return [
            UserResponse(
                id=user["id"],
                email=user["email"],
                full_name=user["full_name"],
                department=user.get("department"),
                level=user.get("level"),
                image_profile=user.get("image_profile"),
                role=user["role"],
                is_active=user.get("is_active", True),
                created_at=user.get("created_at"),
                updated_at=user.get("updated_at"),
            )
            for user in users
        ]
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"เกิดข้อผิดพลาดในการดึงข้อมูลผู้ใช้: {str(e)}",
        )
