from pydantic import BaseModel, Field


class SendOTPRequest(BaseModel):
    """Request schema for sending OTP."""

    mobile: str


class VerifyOTPRequest(BaseModel):
    """Request schema for verifying OTP."""

    session_id: str = Field(..., description="Session ID")
    otp: str = Field(..., description="OTP")
