from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, model_validator
from backend.meta import ComplaintStatus


# Assuming master responses exist or using generic dicts if circular imports arise.

# Checking master.py response schemas would be good, but I'll assume basic structure or use dicts if needed.
# Let's check schemas/response/master.py content in a separate step or assume simple structure.
# Foregoing strict typing on relations for now to avoid complexity without seeing master response definitions.


class MediaResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: int
    media_path: str
    media_type: str
    is_initial: bool
    access_url: Optional[str] = None  # Computed

    model_config = {"from_attributes": True}

    @model_validator(mode="before")
    @classmethod
    def compute_access_url(cls, data):
        from backend.services.storage import generate_signed_file_url
        path = getattr(data, "media_path", None) if hasattr(data, "media_path") else (data.get("media_path") if isinstance(data, dict) else None)
        if path:
            url = generate_signed_file_url(path)
            if isinstance(data, dict):
                data["access_url"] = url
            elif hasattr(data, "__dict__"):
                return {"id": data.id, "media_path": path, "media_type": data.media_type, "is_initial": data.is_initial, "access_url": url}
        return data


class CommentResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: int
    comment: str
    created_at: datetime
    comment_by: Optional[int] = None  # User ID
    media_path: Optional[str] = None
    access_url: Optional[str] = None

    model_config = {"from_attributes": True}

    @model_validator(mode="before")
    @classmethod
    def compute_access_url(cls, data):
        from backend.services.storage import generate_signed_file_url
        path = getattr(data, "media_path", None) if hasattr(data, "media_path") else (data.get("media_path") if isinstance(data, dict) else None)
        if path:
            url = generate_signed_file_url(path)
            if isinstance(data, dict):
                data["access_url"] = url
            elif hasattr(data, "__dict__"):
                return {"id": data.id, "comment": data.comment, "created_at": data.created_at, "comment_by": getattr(data, "comment_by", None), "media_path": path, "access_url": url}
        return data


class ComplaintResponse(BaseModel):
    id: int
    user_id: Optional[int]

    title: str
    description: str

    status: ComplaintStatus

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

    model_config = {
        "from_attributes": True,
        "ignored_types": (ComplaintStatus,)
    }


class ComplaintListResponse(BaseModel):
    items: List[ComplaintResponse] = []
    total: int = 0
    offset: int = 0
    limit: int = 10


class PresignedUrlResponse(BaseModel):
    upload_url: str
    object_key: str
    access_url: str
