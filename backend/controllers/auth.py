from jose import jwt, ExpiredSignatureError, JWTError
from backend.config import settings
import time
import secrets
import string

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, HTTPException, Depends
from fastapi.security import HTTPAuthorizationCredentials
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database import get_db
from backend.services.user import UserService
from backend.services.sms import sms_service
from backend.dao.user import UserDAO, UserRole
from backend.core.security import (
    create_tokens,
    create_access_token,
    decode_token,
    verify_password,
    decrypt_credentials,
    get_rsa_public_key,
)
from backend.middlewares.auth import get_current_user, security
from backend.schemas.base.auth import UserDetails

router = APIRouter()
user_service = UserService()
user_dao = UserDAO()

# --- Request/Response Models ---


class OTPRequest(BaseModel):
    mobile: str


class LoginRequest(BaseModel):
    mobile: str
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
    is_active: bool


# --- Routes ---


@router.post("/send-otp", response_model=MessageResponse)
async def send_otp(request: OTPRequest, db: AsyncSession = Depends(get_db)):
    # Check for existing OTP record (valid or not, to check cooldown)
    latest_otp = await user_dao.get_otp_record(db, request.mobile)
    
    now = datetime.now()
    cooldown_seconds = 120  # 2 minutes cooldown

    if latest_otp:
        elapsed = (now - latest_otp.created_at).total_seconds()
        if elapsed < cooldown_seconds:
            wait_time = int(cooldown_seconds - elapsed)
            raise HTTPException(
                status_code=429,
                detail=f"Please wait {wait_time} seconds before requesting another OTP."
            )

    # Check if a valid (non-expired) OTP already exists to reuse it
    existing_otp = await user_dao.get_valid_otp_record(db, request.mobile)

    if existing_otp:
        # Resend the same OTP
        otp_value = existing_otp.otp
        # Update created_at so the cooldown resets on resend
        existing_otp.created_at = now
        await db.commit()
        
        print("========================================")
        print(f"RESENDING EXISTING OTP {otp_value} TO {request.mobile}")
        print("========================================")
    else:
        # Generate new OTP
        if settings.USE_REAL_OTP:
            otp_value = "".join(secrets.choice(string.digits) for _ in range(6))
        else:
            otp_value = "123456"

        # Store OTP in DB
        await user_dao.create_otp(db, request.mobile, otp_value)

        print("========================================")
        print(f"SENT NEW OTP {otp_value} TO {request.mobile}")
        print("========================================")

    # Trigger SMS delivery
    await sms_service.send_otp(request.mobile, otp_value)

    return {"message": "OTP sent successfully"}


@router.post("/login/otp", response_model=TokenResponse)
async def login_with_otp(request: LoginRequest, db: AsyncSession = Depends(get_db)):
    # Decrypt credentials
    mobile = decrypt_credentials(request.mobile)
    otp = decrypt_credentials(request.otp)

    # 1. Verify OTP
    otp_record = await user_dao.get_otp_record(db, mobile)
    if not otp_record or otp_record.otp != otp:
        raise HTTPException(status_code=400, detail="Invalid OTP")

    # Check expiry
    if otp_record.valid_till < datetime.now():
        raise HTTPException(status_code=400, detail="OTP Expired")

    # 2. OTP is valid, delete it to prevent reuse
    await user_dao.delete_otp_records(db, mobile)

    # 3. Get or create user
    is_new_user = False
    user = await user_service.get_user_by_mobile(db, mobile)

    if not user:
        # Auto-register as citizen
        user = await user_service.create_user(
            db, mobile=mobile, role=UserRole.CITIZEN
        )
        await db.commit()
        await db.refresh(user)
        is_new_user = True
    elif not user.is_active:
        raise HTTPException(status_code=403, detail="User account is inactive")

    # 3. Generate Tokens (access + refresh)
    access_token, refresh_token = create_tokens(user.id, user.role.value, user.token_version)

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
    # Decrypt credentials
    username = decrypt_credentials(request.username)
    password = decrypt_credentials(request.password)

    user = await user_service.get_user_by_username(db, username)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    if not user.is_active:
        raise HTTPException(status_code=403, detail="User account is inactive")

    if not user.password:
        raise HTTPException(
            status_code=401, detail="Password login not enabled for this user"
        )

    if not verify_password(password, user.password):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    # Generate Tokens (access + refresh)
    access_token, refresh_token = create_tokens(user.id, user.role.value, user.token_version)

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "role": user.role.value,
        "user_id": user.id,
        "name": user.name,
    }


@router.get("/public-key")
async def get_public_key():
    """Returns the RSA public key for client-side encryption."""
    return {"public_key": get_rsa_public_key()}


@router.post("/refresh", response_model=RefreshTokenResponse)
async def refresh_access_token(request: RefreshTokenRequest, db: AsyncSession = Depends(get_db)):
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
    user_id_str = payload.get("sub")
    role = payload.get("role")
    token_version = payload.get("version", 1)

    if not user_id_str or not role:
        raise HTTPException(
            status_code=401,
            detail="Invalid refresh token payload",
        )

    user_id = int(user_id_str)
    user = await user_dao.get_by_id(db, user_id)
    if not user or user.token_version != token_version:
        raise HTTPException(
            status_code=401,
            detail="Token invalidated. Please login again.",
        )

    # Create new access token
    token_data = {"sub": str(user_id), "role": role, "version": user.token_version}
    new_access_token = create_access_token(token_data)

    return {
        "access_token": new_access_token,
        "token_type": "bearer",
    }


@router.post("/logout", response_model=MessageResponse)
async def logout(
    current_user: UserDetails = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Logout the current user by incrementing their token_version.
    This invalidates all current access and refresh tokens for this user.
    """
    user = await user_dao.get_by_id(db, current_user.user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.token_version += 1
    await db.commit()

    return {"message": "Logged out successfully. All sessions invalidated."}


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
        "is_active": user.is_active,
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
