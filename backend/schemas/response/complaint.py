from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field


# Assuming master responses exist or using generic dicts if circular imports arise.

# Checking master.py response schemas would be good, but I'll assume basic structure or use dicts if needed.
# Let's check schemas/response/master.py content in a separate step or assume simple structure.
# Foregoing strict typing on relations for now to avoid complexity without seeing master response definitions.


class MediaResponse(BaseModel):
    id: int
    media_path: str
    media_type: str
    is_initial: bool
    access_url: Optional[str] = None  # Computed


class CommentResponse(BaseModel):
    id: int
    comment: str
    created_at: datetime
    comment_by: int  # User ID
    media_path: Optional[str] = None
    access_url: Optional[str] = None


class ComplaintResponse(BaseModel):
    id: int
    user_id: Optional[int]

    title: str
    description: str
    status: str

    ward_id: Optional[int]
    department_id: Optional[int]
    category_id: Optional[int]

    applicant_name: str
    applicant_mobile: str

    latitude: Optional[float]
    longitude: Optional[float]
    location_address: Optional[str]

    created_at: datetime
    updated_at: datetime

    media: List[MediaResponse] = []
    comments: List[CommentResponse] = []

    class Config:
        from_attributes = True


class PresignedUrlResponse(BaseModel):
    upload_url: str
    object_key: str
    access_url: str
