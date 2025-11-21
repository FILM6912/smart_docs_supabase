from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from datetime import datetime, timedelta
from jose import JWTError, jwt
from passlib.context import CryptContext
from typing import Optional
from .model import TokenData
from dotenv import load_dotenv
import os
from ..database.supabase import supabase

load_dotenv()

SECRET_KEY = os.getenv("FASTAPI_SECRET")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES"))

pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/token")

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def get_current_user(token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        
        # ดึงข้อมูล role จาก JWT payload
        role = payload.get("role", "user")
        id = payload.get("id", None)
        full_name = payload.get("full_name", None)
        department = payload.get("department", None)
        
        print("\n\n")
        print(payload)
        
        if email is None:
            raise credentials_exception
        token_data = TokenData(
            id=id,
            email=email,
            role=role,
            full_name=full_name,
            department=department,
        )
    except JWTError:
        raise credentials_exception
    
    # ตรวจสอบสถานะการใช้งานของผู้ใช้จากฐานข้อมูล
    try:
        response = supabase.schema("smart_documents").table("users").select("is_active").eq("id", token_data.id).execute().data
        if not response or not response[0].get("is_active", True):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Account is deactivated",
                headers={"WWW-Authenticate": "Bearer"},
            )
    except HTTPException:
        raise
    except:
        # ถ้าไม่สามารถตรวจสอบจากฐานข้อมูลได้ ให้ใช้ค่าเริ่มต้น (active)
        pass
    
    user = {
        "id": token_data.id,
        "email": token_data.email,
        "full_name": token_data.full_name,
        "role": token_data.role,
        "department": token_data.department,
    }
    return user

async def get_current_active_user(current_user: dict = Depends(get_current_user)):
    if current_user.get("role") not in ["user", "admin", "superadmin"]:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not a valid user"
        )
    return current_user

async def get_current_admin_user(current_user: dict = Depends(get_current_user)):
    if current_user.get("role") not in ["admin", "superadmin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    return current_user

async def get_current_superadmin_user(current_user: dict = Depends(get_current_user)):
    if current_user.get("role") != "superadmin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Superadmin access required"
        )
    return current_user

# ฟังก์ชันสำหรับตรวจสอบสิทธิ์แบบสั้น (ใช้กับ Depends)
async def is_user(current_user: dict = Depends(get_current_user)):
    if current_user.get("role") not in ["user", "admin", "superadmin"]:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User access required"
        )
    return current_user

async def is_admin(current_user: dict = Depends(get_current_user)):
    if current_user.get("role") not in ["admin", "superadmin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    return current_user

async def is_superadmin(current_user: dict = Depends(get_current_user)):
    if current_user.get("role") != "superadmin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Superadmin access required"
        )
    return current_user

def validate_user_token(token: str):
    """
    ตรวจสอบ token ว่าถูกต้องและผู้ใช้มีสถานะ active หรือไม่
    ใช้สำหรับตรวจสอบ token ที่ไม่ได้ผ่าน dependency injection
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("id")
        
        if not user_id:
            return False, "Invalid token"
        
        # ตรวจสอบสถานะการใช้งานของผู้ใช้จากฐานข้อมูล
        response = supabase.schema("smart_documents").table("users").select("is_active").eq("id", user_id).execute().data
        
        if not response:
            return False, "User not found"
        
        if not response[0].get("is_active", True):
            return False, "Account is deactivated"
        
        return True, "Token is valid"
    except JWTError:
        return False, "Invalid token"
    except Exception as e:
        return False, f"Error validating token: {str(e)}"
