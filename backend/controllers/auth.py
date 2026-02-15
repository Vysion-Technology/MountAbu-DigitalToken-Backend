from jose import jwt, ExpiredSignatureError, JWTError
from backend.config import settings
import time

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, HTTPException, Depends
from fastapi.security import HTTPAuthorizationCredentials
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
from backend.middlewares.auth import get_current_user, security
from backend.schemas.base.auth import UserDetails

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
    is_new_user: bool = False


class RefreshTokenResponse(BaseModel):
    access_token: str
    token_type: str


class MessageResponse(BaseModel):
    message: str


class MeResponse(BaseModel):
    user_id: int
    name: str
    mobile: str
    role: str
    username: Optional[str] = None


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

    # 2. Get or create user
    is_new_user = False
    user = await user_service.get_user_by_mobile(db, request.mobile)

    if not user:
        # Auto-register as citizen
        user = await user_service.create_user(
            db, mobile=request.mobile, role=UserRole.CITIZEN
        )
        await db.commit()
        await db.refresh(user)
        is_new_user = True

    # 3. Generate Tokens (access + refresh)
    access_token, refresh_token = create_tokens(user.id, user.role.value)

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "role": user.role.value,
        "user_id": user.id,
        "name": user.name,
        "is_new_user": is_new_user,
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


@router.get("/me", response_model=MeResponse)
async def get_me(
    current_user: UserDetails = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Return the authenticated user's profile.
    Useful for validating the auth flow end-to-end.
    """
    user = await user_dao.get_by_id(db, current_user.user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return {
        "user_id": user.id,
        "name": user.name,
        "mobile": user.mobile,
        "role": user.role.value,
        "username": user.username,
    }


@router.get("/debug-token")
async def debug_token(
    credentials: HTTPAuthorizationCredentials = Depends(security),
):
    """
    DEBUG ONLY: Decode the token and return detailed info about what's wrong.
    Remove this endpoint in production.
    """

    token = credentials.credentials
    now_ts = time.time()

    # First, decode WITHOUT verification to see the payload
    try:
        unverified = jwt.get_unverified_claims(token)
    except Exception as e:
        return {"error": "Cannot parse token at all", "detail": str(e)}

    exp_ts = unverified.get("exp")
    info = {
        "unverified_payload": unverified,
        "server_time_utc": now_ts,
        "token_exp": exp_ts,
        "seconds_until_expiry": (exp_ts - now_ts) if exp_ts else None,
        "is_expired": (now_ts > exp_ts) if exp_ts else "no exp claim",
    }

    # Now try verified decode
    try:
        verified = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        info["verified_payload"] = verified
        info["status"] = "VALID"
    except ExpiredSignatureError:
        info["status"] = "EXPIRED"
        info["error"] = "Token signature is valid but the token has expired"
    except JWTError as e:
        info["status"] = "INVALID"
        info["error"] = str(e)

    return info
