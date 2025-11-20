from supabase import create_client
from dotenv import load_dotenv
from fastapi import HTTPException
import os
from passlib.context import CryptContext
import uuid
import base64

load_dotenv()

url = os.getenv("SUPABASE_URL")
key = os.getenv("ANON_KEY")
service_key = os.getenv("SERVICE_ROLE_KEY", key)  # ใช้ ANON_KEY ถ้าไม่มี SERVICE_ROLE_KEY

supabase = create_client(url, key)
supabase_admin = create_client(url, service_key)  # สร้าง client สำหรับการดำเนินการที่ต้องการสิทธิ์สูงกว่า

pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")


def signup_supabase(email: str, password: str, full_name: str,department: str):

    if (
        supabase.schema("smart_documents")
        .table("users")
        .select("*")
        .eq("email", email)
        .execute()
        .data
    ):
        raise HTTPException(status_code=409, detail="Email already registered")

    try:
        response = (
            supabase.schema("smart_documents")
            .table("users")
            .insert({"email": email, "password": password, "full_name": full_name,"department":department.lower()})
            .execute()
            .data
        )
    except:
        raise HTTPException(status_code=500, detail="Internal server error")

    return {
        "id": response[0]["id"],
        "email": response[0]["email"],
        "full_name": response[0]["full_name"],
        "department": response[0]["department"],
    }


def login_supabase(
    email: str,
    password: str,
):
    try:
        response = (
            supabase.schema("smart_documents")
            .table("users")
            .select("*")
            .eq("email", email)
            .execute()
            .data
        )
        if response == []:
            raise HTTPException(status_code=401, detail="Invalid email or password")
        
        # ตรวจสอบรหัสผ่านที่ถูกเข้ารหัส
        user = response[0]
        if not pwd_context.verify(password, user["password"]):
            raise HTTPException(status_code=401, detail="Invalid email or password")
        
        # ตรวจสอบสถานะการใช้งานของผู้ใช้
        if not user.get("is_active", True):  # ค่าเริ่มต้นเป็น True ถ้าไม่มีฟิลด์นี้
            raise HTTPException(status_code=403, detail="Account is deactivated")
            
        return user
    except HTTPException:
        raise
    except:
        raise HTTPException(status_code=500, detail="Internal server error")


def update_user_profile(user_id: str, update_data: dict):
    try:
        response = (
            supabase.schema("smart_documents")
            .table("users")
            .update(update_data)
            .eq("id", user_id)
            .execute()
            .data
        )
        if response == []:
            raise HTTPException(status_code=404, detail="User not found")
        return response[0]
    except HTTPException:
        raise
    except:
        raise HTTPException(status_code=500, detail="Internal server error")


def upload_profile_image(user_id: str, image_data: str, filename: str = None):
    try:
        # ตรวจสอบประเภทของรูปภาพเพื่อกำหนดนามสกุลไฟล์
        file_extension = "jpg"  # ค่าเริ่มต้น
        content_type = "image/jpeg"  # ค่าเริ่มต้น
        
        if "," in image_data:
            # ถ้าเป็น base64 data URL ให้แยกส่วน header ออก
            header = image_data.split(",")[0]
            image_data = image_data.split(",")[1]
            
            # ตรวจสอบประเภทของรูปภาพจาก header
            if "data:image/png" in header:
                file_extension = "png"
                content_type = "image/png"
            elif "data:image/gif" in header:
                file_extension = "gif"
                content_type = "image/gif"
            elif "data:image/webp" in header:
                file_extension = "webp"
                content_type = "image/webp"
            elif "data:image/bmp" in header:
                file_extension = "bmp"
                content_type = "image/bmp"
            elif "data:image/svg+xml" in header:
                file_extension = "svg"
                content_type = "image/svg+xml"
            # ค่าเริ่มต้นคือ jpg/jpeg
        
        # ใช้ user_id เป็นชื่อไฟล์
        filename = f"{user_id}.{file_extension}"
        
        # แปลง base64 เป็น binary
        image_bytes = base64.b64decode(image_data)
        
        # อัปโหลดไปยัง Supabase Storage
        storage_path = f"{filename}"
        response = supabase.storage.from_("image_profile").upload(
            path=storage_path,
            file=image_bytes,
            file_options={"content-type": content_type, "upsert": "true"}
        )
        
        # ดึง URL สาธารณะของรูปภาพ
        public_url = supabase.storage.from_("image_profile").get_public_url(storage_path)
        
        # อัปเดต URL ในฐานข้อมูลผู้ใช้
        update_response = update_user_profile(user_id, {"image_profile": public_url})
        
        return {
            "url": public_url,
            "path": storage_path,
            "user": update_response
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to upload image: {str(e)}")


def delete_user_profile_image(user_id: str):
    """
    ลบรูปโปรไฟล์ของผู้ใช้จาก Supabase Storage
    """
    try:
        # ดึงข้อมูลผู้ใช้เพื่อหา URL ของรูปภาพ
        user_data = supabase.schema("smart_documents").table("users").select("image_profile").eq("id", user_id).execute().data
        
        if not user_data:
            return {"success": False, "message": "ไม่พบผู้ใช้"}
        
        user = user_data[0]
        image_url = user.get("image_profile")
        
        if not image_url:
            return {"success": True, "message": "ไม่มีรูปโปรไฟล์ให้ลบ"}
        
        # แยกเส้นทางไฟล์จาก URL
        # URL จะอยู่ในรูปแบบ: https://[project-ref].supabase.co/storage/v1/object/public/image_profile/[filename]
        print(f"URL ต้นฉบับ: {image_url}")
        
        # แยกชื่อไฟล์จาก URL
        # ใช้วิธีการแยกจาก URL โดยตรงแทนการสร้างจาก user_id
        try:
            # แยกชื่อไฟล์จาก URL
            file_name = image_url.split("/")[-1]
            print(f"ชื่อไฟล์ที่ตรวจพบจาก URL: {file_name}")
            
            # ลองลบไฟล์โดยใช้ supabase_admin ที่มีสิทธิ์สูงกว่า
            result = supabase_admin.storage.from_("image_profile").remove([file_name])
            print(f"ผลลัพธ์การลบ {file_name}: {result}")
            
            # ตรวจสอบว่าการลบสำเร็จหรือไม่
            # ใน Supabase Python client หากไม่มี error แสดงว่าการลบสำเร็จ
            if result is not None:
                print(f"ลบไฟล์ {file_name} สำเร็จ")
                return {"success": True, "message": f"ลบรูปโปรไฟล์สำเร็จ: {file_name}"}
        except Exception as delete_error:
            print(f"ไม่สามารถลบไฟล์ {file_name}: {str(delete_error)}")
        
        # ถ้าไม่สามารถลบไฟล์จาก URL ได้ ให้ลองลบจาก user_id กับทุกนามสกุลที่เป็นไปได้
        file_extensions = ["jpg", "jpeg", "png", "gif", "webp", "bmp", "svg"]
        
        # ลองลบไฟล์กับทุกนามสกุลที่เป็นไปได้
        for ext in file_extensions:
            file_path = f"{user_id}.{ext}"
            print(f"กำลังพยายามลบไฟล์: {file_path}")
            
            try:
                # ลองลบไฟล์โดยใช้ supabase_admin ที่มีสิทธิ์สูงกว่า
                result = supabase_admin.storage.from_("image_profile").remove([file_path])
                print(f"ผลลัพธ์การลบ {file_path}: {result}")
                
                # ตรวจสอบว่าการลบสำเร็จหรือไม่
                # ใน Supabase Python client หากไม่มี error แสดงว่าการลบสำเร็จ
                if result is not None:
                    print(f"ลบไฟล์ {file_path} สำเร็จ")
                    return {"success": True, "message": f"ลบรูปโปรไฟล์สำเร็จ: {file_path}"}
            except Exception as delete_error:
                print(f"ไม่สามารถลบไฟล์ {file_path}: {str(delete_error)}")
                # ลองนามสกุลถัดไป
        
        # ถ้าไม่สามารถลบไฟล์ใดๆ ได้
        return {"success": False, "message": "ไม่พบไฟล์รูปโปรไฟล์ที่ตรงกับ user_id ใน storage"}
    except Exception as e:
        return {"success": False, "message": f"เกิดข้อผิดพลาดในการลบรูป: {str(e)}"}
