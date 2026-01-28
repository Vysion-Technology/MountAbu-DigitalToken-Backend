from pydantic import BaseModel, Field


class SendOTPResponse(BaseModel):
    """Response schema for sending OTP."""

    session_id: str = Field(..., description="Session ID")


class LoginSuccessResponse(BaseModel):
    """Response schema for successful login."""

    access_token: str = Field(..., description="Access token")
    refresh_token: str = Field(..., description="Refresh token")
