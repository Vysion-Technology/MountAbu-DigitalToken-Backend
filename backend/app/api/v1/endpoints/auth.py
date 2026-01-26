"""Authentication endpoints."""

import secrets
from datetime import datetime, timedelta, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    generate_otp,
    hash_password,
    verify_password,
)
from app.models import User, UserType, OTPSession
from app.schemas import (
    LoginRequest,
    LoginResponse,
    VerifyOTPRequest,
    TokenResponse,
    RefreshTokenRequest,
    SuccessResponse,
    ErrorResponse,
)
from app.services.sms_service import send_otp_sms

router = APIRouter()


@router.post("/login", response_model=SuccessResponse)
async def login(
    request: LoginRequest,
    background_tasks: BackgroundTasks,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Initiate login process.
    - For applicants: Send OTP to mobile
    - For authorities: Verify password, then send OTP
    """
    # Find user
    if request.user_type == "applicant":
        # Find by mobile
        result = await db.execute(
            select(User).where(
                User.mobile == request.identifier,
                User.user_type == UserType.APPLICANT,
                User.is_deleted == False,
            )
        )
        user = result.scalar_one_or_none()

        # For applicants, create user if not exists
        if not user:
            user = User(
                user_type=UserType.APPLICANT,
                name="New User",  # Will be updated during profile completion
                mobile=request.identifier,
            )
            db.add(user)
            await db.flush()

    else:  # authority
        if not request.password:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Password required for authority login",
            )

        # Find by email
        result = await db.execute(
            select(User).where(
                User.email == request.identifier,
                User.user_type == UserType.AUTHORITY,
                User.is_deleted == False,
            )
        )
        user = result.scalar_one_or_none()

        if not user or not verify_password(request.password, user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password",
            )

    # Check if user is blacklisted (only for applicants)
    if user.user_type == UserType.APPLICANT and user.blacklist_status:
        if user.blacklist_status.is_blacklisted:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "code": "USER_BLACKLISTED",
                    "message": "Your account is blacklisted. Please visit SDM office.",
                    "blacklisted_at": str(user.blacklist_status.blacklisted_at),
                },
            )

    # Generate OTP
    otp = generate_otp()
    session_id = f"sess_{secrets.token_urlsafe(16)}"

    # Store OTP session
    otp_session = OTPSession(
        session_id=session_id,
        identifier=request.identifier,
        user_type=UserType.APPLICANT
        if request.user_type == "applicant"
        else UserType.AUTHORITY,
        otp_hash=hash_password(otp),  # Hash the OTP
        expires_at=datetime.now(timezone.utc)
        + timedelta(seconds=settings.OTP_EXPIRE_SECONDS),
    )
    db.add(otp_session)

    # Send OTP via SMS (in background)
    mobile = user.mobile if user.mobile else request.identifier
    background_tasks.add_task(send_otp_sms, mobile, otp)

    # Mask mobile for response
    masked_mobile = f"****{mobile[-4:]}" if mobile else None

    return SuccessResponse(
        data=LoginResponse(
            session_id=session_id,
            otp_sent=True,
            otp_expires_in=settings.OTP_EXPIRE_SECONDS,
            masked_mobile=masked_mobile,
        ).model_dump()
    )


@router.post("/verify-otp", response_model=SuccessResponse)
async def verify_otp(
    request: VerifyOTPRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Verify OTP and complete login."""
    # Find OTP session
    result = await db.execute(
        select(OTPSession).where(
            OTPSession.session_id == request.session_id,
            OTPSession.verified == False,
        )
    )
    otp_session = result.scalar_one_or_none()

    if not otp_session:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired session",
        )

    # Check expiry
    if datetime.now(timezone.utc) > otp_session.expires_at:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="OTP expired",
        )

    # Check attempts
    if otp_session.attempts >= 3:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Too many failed attempts. Please request a new OTP.",
        )

    # Verify OTP
    if not verify_password(request.otp, otp_session.otp_hash):
        otp_session.attempts += 1
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid OTP",
        )

    # Mark as verified
    otp_session.verified = True

    # Find user
    if otp_session.user_type == UserType.APPLICANT:
        result = await db.execute(
            select(User).where(User.mobile == otp_session.identifier)
        )
    else:
        result = await db.execute(
            select(User).where(User.email == otp_session.identifier)
        )
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    # Update login info
    user.last_login_at = datetime.now(timezone.utc)
    user.login_count += 1
    user.mobile_verified = True

    # Generate tokens
    access_token = create_access_token(
        subject=str(user.id),
        user_type=user.user_type.value,
    )
    refresh_token = create_refresh_token(
        subject=str(user.id),
        user_type=user.user_type.value,
    )

    return SuccessResponse(
        data={
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "Bearer",
            "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            "user": {
                "id": str(user.id),
                "name": user.name,
                "mobile": user.mobile,
                "email": user.email,
                "user_type": user.user_type.value,
                "aadhaar_verified": user.aadhaar_verified,
            },
        }
    )


@router.post("/refresh", response_model=SuccessResponse)
async def refresh_token(
    request: RefreshTokenRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Refresh access token."""
    payload = decode_token(request.refresh_token)

    if not payload or payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
        )

    # Verify user still exists and is active
    result = await db.execute(
        select(User).where(User.id == payload["sub"], User.is_deleted == False)
    )
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )

    # Generate new access token
    access_token = create_access_token(
        subject=str(user.id),
        user_type=user.user_type.value,
    )

    return SuccessResponse(
        data={
            "access_token": access_token,
            "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        }
    )


@router.post("/logout", response_model=SuccessResponse)
async def logout():
    """Logout user (client-side token invalidation)."""
    # For stateless JWT, logout is handled client-side
    # In production, you might want to add token to a blacklist
    return SuccessResponse(message="Logged out successfully")
