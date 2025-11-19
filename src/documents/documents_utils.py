import base64
import uuid
import re
from ..database.supabase import supabase, supabase_admin
from .model import ImageReference

def upload_image_to_supabase(img_byte: str, file_name: str, doc_id: int = None) -> str:
    """
    อัปโหลดรูปภาพไปยัง Supabase Storage และคืนค่า URL ของรูปภาพ
    """
    try:
        # ตรวจสอบประเภทของรูปภาพเพื่อกำหนดนามสกุลไฟล์
        file_extension = "png"  # ค่าเริ่มต้น
        content_type = "image/png"  # ค่าเริ่มต้น
        
        # แยกส่วน header และตรวจสอบประเภทของรูปภาพ
        if "," in img_byte:
            # ถ้าเป็น base64 data URL ให้แยกส่วน header ออก
            header = img_byte.split(",")[0]
            img_byte = img_byte.split(",")[1]
            
            # ตรวจสอบประเภทของรูปภาพจาก header
            if "data:image/png" in header:
                file_extension = "png"
                content_type = "image/png"
            elif "data:image/jpeg" in header or "data:image/jpg" in header:
                file_extension = "jpg"
                content_type = "image/jpeg"
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
        elif img_byte.startswith('data:image'):
            # กรณีที่มีแค่ prefix แต่ไม่มี comma
            if "data:image/png" in img_byte:
                file_extension = "png"
                content_type = "image/png"
            elif "data:image/jpeg" in img_byte or "data:image/jpg" in img_byte:
                file_extension = "jpg"
                content_type = "image/jpeg"
            elif "data:image/gif" in img_byte:
                file_extension = "gif"
                content_type = "image/gif"
            elif "data:image/webp" in img_byte:
                file_extension = "webp"
                content_type = "image/webp"
            elif "data:image/bmp" in img_byte:
                file_extension = "bmp"
                content_type = "image/bmp"
            elif "data:image/svg+xml" in img_byte:
                file_extension = "svg"
                content_type = "image/svg+xml"
            
            # แยกส่วน header ออก
            img_byte = img_byte.split(',')[1] if ',' in img_byte else img_byte
        
        # แปลง base64 เป็น bytes
        img_data = base64.b64decode(img_byte)
        
        # สร้างชื่อไฟล์สุ่ม
        unique_id = str(uuid.uuid4())
        
        # สร้าง path ตามรูปแบบที่ต้องการ: {doc_id}/{filename}
        # ไม่ต้องใส่ documents_images นำหน้าเพราะจะถูกเพิ่มโดยอัตโนมัติจาก bucket
        if doc_id is not None:
            storage_path = f"{doc_id}/{unique_id}_{file_name}"
        else:
            # กรณีสร้างเอกสารใหม่ ยังไม่มี doc_id ใช้ temp_id แทน
            temp_id = str(uuid.uuid4())
            storage_path = f"temp_{temp_id}/{unique_id}_{file_name}"
        
        # อัปโหลดไปยัง Supabase Storage
        # ใช้ bucket ชื่อ "documents_images"
        result = supabase.storage.from_("documents_images").upload(
            path=storage_path,
            file=img_data,
            file_options={"content-type": content_type}
        )
        
        # ดึง public URL
        public_url = supabase.storage.from_("documents_images").get_public_url(storage_path)
        
        return public_url
    except Exception as e:
        print(f"Error uploading image: {str(e)}")
        # ถ้าอัปโหลดไม่สำเร็จ คืนค่า None
        return None

def replace_blob_urls_with_image_urls(content: str, img_refs: list[ImageReference], doc_id: int = None) -> tuple[str, list]:
    """
    แทนที่ blob URLs ใน content ด้วย URLs ของรูปภาพที่อัปโหลดแล้ว
    คืนค่า (content ที่แก้ไขแล้ว, รายการ URLs ของรูปภาพที่อัปโหลดสำเร็จ)
    """
    updated_content = content
    uploaded_urls = []
    
    for img_ref in img_refs:
        # ดึง blob URL จาก refer
        blob_url_match = re.search(r'\(blob:([^)]+)\)', img_ref.refer)
        if blob_url_match:
            blob_url = f"blob:{blob_url_match.group(1)}"
            
            # อัปโหลดรูปภาพ
            img_url = upload_image_to_supabase(img_ref.imgByte, f"image_{len(uploaded_urls)}.png", doc_id)
            
            if img_url:
                # แทนที่ blob URL ด้วย URL ของรูปภาพที่อัปโหลดแล้ว
                updated_content = updated_content.replace(blob_url, img_url)
                uploaded_urls.append(img_url)
    
    return updated_content, uploaded_urls

def process_document_images(content: str, img_refs: list[ImageReference], doc_id: int) -> str:
    """
    ประมวลผลรูปภาพในเอกสาร โดยอัปโหลดรูปภาพและแทนที่ blob URLs
    คืนค่า content ที่อัปเดตแล้ว
    """
    updated_content, uploaded_urls = replace_blob_urls_with_image_urls(content, img_refs, doc_id)
    return updated_content

def delete_document_images(doc_id: int) -> bool:
    """
    ลบรูปภาพทั้งหมดที่เกี่ยวข้องกับเอกสาร
    คืนค่า True ถ้าสำเร็จ, False ถ้าไม่สำเร็จ
    """
    try:
        # ดึงรายการไฟล์ทั้งหมดในโฟลเดอร์ {doc_id}/
        folder_path = f"{doc_id}/"
        
        # ลิสต์ไฟล์ในโฟลเดอร์
        files = supabase.storage.from_("documents_images").list(folder_path)
        
        # ถ้ามีไฟล์ให้ลบทั้งหมด
        if files:
            file_paths = [f"{folder_path}{file['name']}" for file in files]
            # ใช้ supabase_admin สำหรับการลบไฟล์เพื่อให้มีสิทธิ์เพียงพอ
            result = supabase_admin.storage.from_("documents_images").remove(file_paths)
            print(f"ผลลัพธ์การลบรูปภาพของเอกสาร {doc_id}: {result}")
        
        return True
    except Exception as e:
        print(f"Error deleting images for document {doc_id}: {str(e)}")
        return False