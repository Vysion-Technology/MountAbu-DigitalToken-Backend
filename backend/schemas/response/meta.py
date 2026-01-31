from pydantic import BaseModel, Field


class SuccessResponse(BaseModel):
    """Generic success response."""

    success: bool = True


class MessageResponse(BaseModel):
    """Response with a message."""

    message: str = Field(..., description="Response message")


class DocumentUploadResponse(BaseModel):
    """Response after uploading a document."""

    message: str = Field(..., description="Success message")
    path: str = Field(..., description="Path where document was uploaded")


class UserCreatedResponse(BaseModel):
    """Response after creating a user."""

    message: str = Field(..., description="Success message")
    user_id: int = Field(..., description="ID of the created user")
