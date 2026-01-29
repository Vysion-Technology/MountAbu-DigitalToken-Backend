from datetime import datetime

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database import get_db
from backend.services.user import UserService
from backend.dao.user import UserDAO, UserRole
from backend.core.security import (
    create_tokens,
    create_access_token,
    decode_token,
    verify_password,
)

router = APIRouter()
user_service = UserService()
user_dao = UserDAO()

# --- Request/Response Models ---


class OTPRequest(BaseModel):
    mobile: str = Field(..., pattern=r"^\d{10}$")


class LoginRequest(BaseModel):
    mobile: str = Field(..., pattern=r"^\d{10}$")
    otp: str


class PasswordLoginRequest(BaseModel):
    username: str
    password: str


class SignupRequest(BaseModel):
    mobile: str = Field(..., pattern=r"^\d{10}$")
    otp: str
    name: str


class RefreshTokenRequest(BaseModel):
    refresh_token: str = Field(
        ..., description="The refresh token to exchange for a new access token"
    )


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str
    role: str
    user_id: int
    name: str


class RefreshTokenResponse(BaseModel):
    access_token: str
    token_type: str


class MessageResponse(BaseModel):
    message: str


# --- Routes ---


@router.post("/send-otp", response_model=MessageResponse)
async def send_otp(request: OTPRequest, db: AsyncSession = Depends(get_db)):
    # Check if a valid (non-expired) OTP already exists
    existing_otp = await user_dao.get_valid_otp_record(db, request.mobile)

    if existing_otp:
        # Resend the same OTP if it hasn't expired
        otp_value = existing_otp.otp
        print("========================================")
        print(f"RESENDING EXISTING OTP {otp_value} TO {request.mobile}")
        print("========================================")
    else:
        # Generate new OTP (placeholder: using "123456" for everyone)
        otp_value = "123456"

        # Store OTP in DB
        await user_dao.create_otp(db, request.mobile, otp_value)

        print("========================================")
        print(f"SENT NEW OTP {otp_value} TO {request.mobile}")
        print("========================================")

    return {"message": "OTP sent successfully"}


@router.post("/login/otp", response_model=TokenResponse)
async def login_with_otp(request: LoginRequest, db: AsyncSession = Depends(get_db)):
    # 1. Verify OTP
    otp_record = await user_dao.get_otp_record(db, request.mobile)
    if not otp_record or otp_record.otp != request.otp:
        raise HTTPException(status_code=400, detail="Invalid OTP")

    # Check expiry
    if otp_record.valid_till < datetime.now():
        raise HTTPException(status_code=400, detail="OTP Expired")

    # 2. Get User
    user = await user_service.get_user_by_mobile(db, request.mobile)
    if not user:
        raise HTTPException(status_code=404, detail="User not found. Please sign up.")

    # 3. Generate Tokens (access + refresh)
    access_token, refresh_token = create_tokens(user.id, user.role.value)

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "role": user.role.value,
        "user_id": user.id,
        "name": user.name,
    }


@router.post("/signup", response_model=TokenResponse)
async def signup_citizen(request: SignupRequest, db: AsyncSession = Depends(get_db)):
    # 1. Verify OTP
    otp_record = await user_dao.get_otp_record(db, request.mobile)
    if not otp_record or otp_record.otp != request.otp:
        raise HTTPException(status_code=400, detail="Invalid OTP")

    if otp_record.valid_till < datetime.now():
        raise HTTPException(status_code=400, detail="OTP Expired")

    # 2. Check if already exists
    existing_user = await user_service.get_user_by_mobile(db, request.mobile)
    if existing_user:
        raise HTTPException(status_code=400, detail="User already registered.")

    # 3. Create User
    user = await user_service.create_user(
        db, request.mobile, request.name, UserRole.CITIZEN
    )

    # Commit
    await db.commit()
    await db.refresh(user)

    # 4. Generate Tokens (access + refresh)
    access_token, refresh_token = create_tokens(user.id, user.role.value)

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "role": user.role.value,
        "user_id": user.id,
        "name": user.name,
    }


@router.post("/login/password", response_model=TokenResponse)
async def login_with_password(
    request: PasswordLoginRequest, db: AsyncSession = Depends(get_db)
):
    user = await user_service.get_user_by_username(db, request.username)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    if not user.password:
        raise HTTPException(
            status_code=401, detail="Password login not enabled for this user"
        )

    if not verify_password(request.password, user.password):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    # Generate Tokens (access + refresh)
    access_token, refresh_token = create_tokens(user.id, user.role.value)

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "role": user.role.value,
        "user_id": user.id,
        "name": user.name,
    }


@router.post("/refresh", response_model=RefreshTokenResponse)
async def refresh_access_token(request: RefreshTokenRequest):
    """
    Exchange a valid refresh token for a new access token.

    The refresh token itself is NOT rotated - it remains valid until its 90-day expiry.
    Only a new access token (30 min expiry) is returned.
    """
    # Decode and validate the refresh token
    payload = decode_token(request.refresh_token)

    if not payload:
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired refresh token",
        )

    # Verify it's a refresh token (not an access token)
    token_type = payload.get("type")
    if token_type != "refresh":
        raise HTTPException(
            status_code=401,
            detail="Invalid token type. Please provide a refresh token.",
        )

    # Extract user info from refresh token
    user_id = payload.get("sub")
    role = payload.get("role")

    if not user_id or not role:
        raise HTTPException(
            status_code=401,
            detail="Invalid refresh token payload",
        )

    # Create new access token
    token_data = {"sub": user_id, "role": role}
    new_access_token = create_access_token(token_data)

    return {
        "access_token": new_access_token,
        "token_type": "bearer",
    }
