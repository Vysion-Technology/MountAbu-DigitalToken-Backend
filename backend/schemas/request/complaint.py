from typing import List, Optional
from pydantic import BaseModel, Field


class PresignedUrlRequest(BaseModel):
    filename: str = Field(..., description="Name of the file to upload")
    content_type: str = Field(..., description="MIME type of the file")
    category: str = Field(..., description="Category: 'application' or 'complaint'")
    entity_id: Optional[int] = Field(
        None,
        description="ID of existing entity. If None, assumes new entity (temp path).",
    )


class ComplaintCreateRequest(BaseModel):
    title: str = Field(..., min_length=5, description="Complaint Title")
    description: str = Field(..., min_length=10, description="Detailed Description")

    ward_id: Optional[int] = None
    category_id: Optional[int] = None

    applicant_name: str = Field(..., description="Name of applicant")
    applicant_mobile: str = Field(
        ..., pattern=r"^\+?[1-9]\d{1,14}$", description="Mobile number"
    )

    latitude: Optional[float] = None
    longitude: Optional[float] = None
    location_address: Optional[str] = None

    media_keys: List[str] = Field(
        default_factory=list, description="List of S3 keys from presigned upload"
    )


class CommentCreateRequest(BaseModel):
    comment: str = Field(..., min_length=1)
    media_keys: List[str] = Field(
        default_factory=list, description="Attached media keys"
    )


class ComplaintMediaAddRequest(BaseModel):
    media_keys: List[str] = Field(
        ..., min_length=1, description="List of media keys to add"
    )
