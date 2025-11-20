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
from datetime import datetime, timezone
from dotenv import load_dotenv
from jose import JWTError, jwt

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

@router.get("/check-token", response_model=dict)
async def check_token_expiry(token: str):
    """
    ตรวจสอบว่า access-token หมดอายุหรือยัง และคำนวณเวลาที่เหลือ
    พร้อมตรวจสอบสถานะการใช้งานของผู้ใช้
    """
    from .auth_utils import validate_user_token
    
    token = token.replace("Bearer ", "") if token.startswith("Bearer ") else token

    # ตรวจสอบความถูกต้องของ token และสถานะผู้ใช้
    is_valid, message = validate_user_token(token)
    if not is_valid:
        return {
            "is_valid": False,
            "is_expired": True,
            "message": message,
            "remaining_days": 0,
            "remaining_human": "Token ไม่ถูกต้องหรือบัญชีถูกปิดใช้งาน"
        }

    try:
        # decode โดยไม่ verify signature และไม่ verify expiration
        payload = jwt.decode(
            token,
            key="",
            options={
                "verify_signature": False,
                "verify_exp": False  # ← เพิ่มบรรทัดนี้
            }
        )
        exp = payload.get("exp")
        if not exp:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Token ไม่มีข้อมูลวันหมดอายุ"
            )

        exp_dt = datetime.fromtimestamp(exp, tz=timezone.utc)
        now = datetime.now(timezone.utc)
        remaining = exp_dt - now

        if remaining.total_seconds() <= 0:
            return {
                "is_valid": False,
                "is_expired": True,
                "remaining_days": 0,
                "remaining_human": "หมดอายุแล้ว"
            }

        days = remaining.days
        hours, remainder = divmod(remaining.seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        
        human_str = f"{days} day {hours:02d}:{minutes:02d}:{seconds:02d}"

        return {
            "is_valid": True,
            "is_expired": False,
            "expiry_at_utc": exp_dt.isoformat(),
            "remaining_days": days,
            "remaining_human": human_str
        }
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Token ไม่ถูกต้องหรือไม่สามารถอ่านได้"
        )