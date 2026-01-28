from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field

router = APIRouter()

class LoginRequest(BaseModel):
    mobile: str = Field(..., pattern=r"^\d{10}$")

class LoginResponse(BaseModel):
    message: str

class VerifyRequest(BaseModel):
    mobile: str
    otp: str

class VerifyResponse(BaseModel):
    token: str
    user_id: int  # Mock
    message: str

# Placeholder for sending OTP
def send_otp(mobile: str, otp: str):
    print("========================================")
    print(f"SENT OTP {otp} TO {mobile}")
    print("========================================")

@router.post("/login", response_model=LoginResponse)
async def login(request: LoginRequest):
    # Logic: Validate user (optional), generate OTP, send OTP
    # For now, just send dummy 123456
    send_otp(request.mobile, "123456")
    return {"message": "OTP sent successfully"}

@router.post("/verify", response_model=VerifyResponse)
async def verify(request: VerifyRequest):
    if request.otp == "123456":
        # Check if user exists in DB, if not create?
        # For this setup I'll just return success mock
        return {
            "token": "mock_access_token_jwt_placeholder",
            "user_id": 1,
            "message": "Login successful",
        }
    raise HTTPException(status_code=400, detail="Invalid OTP")
