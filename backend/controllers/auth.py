from datetime import datetime

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database import get_db
from backend.services.user import UserService
from backend.dao.user import UserDAO, UserRole
from backend.core.security import create_access_token, verify_password

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


class TokenResponse(BaseModel):
    access_token: str
    token_type: str
    role: str
    user_id: int
    name: str

class MessageResponse(BaseModel):
    message: str


# --- Routes ---


@router.post("/send-otp", response_model=MessageResponse)
async def send_otp(request: OTPRequest, db: AsyncSession = Depends(get_db)):
    # Placeholder: Sending the same OTP "123456" for everyone as per request
    otp_value = "123456"

    # Store OTP in DB
    await user_dao.create_otp(db, request.mobile, otp_value)

    # Simulate sending
    print("========================================")
    print(f"SENT OTP {otp_value} TO {request.mobile}")
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

    # 3. Generate Token
    token = create_access_token({"sub": str(user.id), "role": user.role.value})

    return {
        "access_token": token,
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

    # 4. Generate Token
    token = create_access_token({"sub": str(user.id), "role": user.role.value})

    return {
        "access_token": token,
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

    token = create_access_token({"sub": str(user.id), "role": user.role.value})

    return {
        "access_token": token,
        "token_type": "bearer",
        "role": user.role.value,
        "user_id": user.id,
        "name": user.name,
    }
