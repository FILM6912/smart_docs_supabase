from fastapi import APIRouter, Depends, HTTPException, status, Form
from fastapi.security import OAuth2PasswordRequestForm
from datetime import timedelta
from .model import UserLogin, UserResponse, UserCreate, Token
from .auth_utils import (
    create_access_token,
    get_password_hash,
    get_current_user,
    is_user,
    is_admin,
    is_superadmin,
)
from ..database import login_supabase, signup_supabase
import os
from dotenv import load_dotenv

load_dotenv()

ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES"))

router = APIRouter()


@router.post("/login", response_model=Token)
async def login(email: str = Form(...), password: str = Form(...)):
    """
    Login to get access token using query parameters.

    **Usage**: /auth/login?email=your_email@example.com&password=your_password
    """
    # ในสถานการณ์จริง คุณจะต้องตรวจสอบข้อมูลผู้ใช้จากฐานข้อมูล
    user = login_supabase(email, password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # ดึงข้อมูล id และ role จากผู้ใช้
    id = user.get("id", "1")
    role = user.get("role", "user")
    department = user.get("department")
    print(user)

    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={
            "sub": email,
            "id": id,
            "role": role,
            "full_name": user["full_name"],
            "department": department,
        },
        expires_delta=access_token_expires,
    )
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "id": id,
        "email": user["email"],
        "full_name": user["full_name"],
        "role": role,
        "department": department,
    }


@router.post("/token", response_model=Token)
async def login_for_access_token(username: str = Form(...), password: str = Form(...)):
    """
    OAuth2 compatible token login for Swagger UI.

    This endpoint accepts form data with username and password fields.
    The username field should contain the email address.
    """
    # Swagger UI ส่งค่า username/password มาในฟอร์ม ใช้ username เป็นอีเมล
    email = username

    # ตรวจสอบข้อมูลผู้ใช้จากฐานข้อมูล
    user = login_supabase(email, password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # ดึงข้อมูล id และ role จากผู้ใช้
    id = user.get("id", "1")
    role = user.get("role", "user")
    department = user.get("department")

    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={
            "sub": email,
            "id": id,
            "role": role,
            "full_name": user["full_name"],
            "department": department,
        },
        expires_delta=access_token_expires,
    )
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "id": id,
        "email": user["email"],
        "full_name": user["full_name"],
        "role": role,
        "department": department,
    }


@router.post(
    "/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED
)
async def create_user(
    email: str = Form(...), password: str = Form(...), full_name: str = Form(...),department: str = Form(...)
):
    """
    Register a new user using query parameters.

    **Usage**: /auth/register?email=your_email@example.com&password=your_password&full_name=Your Name

    **Note**: By default, new users will have 'user' role unless specified.
    """
    hashed_password = get_password_hash(password)
    return signup_supabase(email=email, password=hashed_password, full_name=full_name,department=department)
