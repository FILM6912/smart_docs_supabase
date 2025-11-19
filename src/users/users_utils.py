from ..auth.auth_utils import (
    create_access_token,
    get_password_hash,
    get_current_user,
    is_user,
    is_admin,
    is_superadmin,
)
from ..database import supabase

def update_user_profile(user_id: str, profile_data: dict):
    """อัปเดตข้อมูลโปรไฟล์ผู้ใช้"""
    try:
        response = supabase.table('users').update(profile_data).eq('id', user_id).execute()
        return response.data[0] if response.data else None
    except Exception as e:
        print(f"❌ Error updating profile: {e}")
        return None

def delete_user_profile(user_id: str):
    """ลบข้อมูลโปรไฟล์ผู้ใช้"""
    try:
        response = supabase.table('users').delete().eq('id', user_id).execute()
        return response.data[0] if response.data else None
    except Exception as e:
        print(f"❌ Error deleting profile: {e}")
        return None
