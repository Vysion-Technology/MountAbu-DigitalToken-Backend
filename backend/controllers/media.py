from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from typing import Optional
import uuid
from backend.services.storage import get_storage_service
from backend.schemas.request.complaint import PresignedUrlRequest
from backend.schemas.response.complaint import PresignedUrlResponse
from pydantic import BaseModel

router = APIRouter()


class MediaUploadResponse(BaseModel):
    object_key: str
    access_url: str
    message: str = "File uploaded successfully"


def _build_object_key(category: str, entity_id: Optional[int], filename: str) -> str:
    """Build a storage object key from category, entity ID, and filename."""
    if entity_id:
        entity_part = str(entity_id)
    else:
        entity_part = f"temp/{uuid.uuid4()}"
    clean_filename = filename.replace(" ", "_").replace("/", "").replace("\\", "")
    return f"{category}/{entity_part}/{clean_filename}"


@router.post("/media/upload", response_model=MediaUploadResponse)
async def upload_media(
    file: UploadFile = File(...),
    category: str = Form("application"),
    entity_id: Optional[int] = Form(None),
):
    """Upload a file directly through the backend (proxied to MinIO).

    This avoids the need for clients to talk to MinIO directly.
    """
    storage = get_storage_service()
    if not storage:
        raise HTTPException(status_code=500, detail="Storage service unavailable")

    object_key = _build_object_key(category, entity_id, file.filename)
    content = await file.read()
    content_type = file.content_type or "application/octet-stream"

    storage.upload_bytes(object_key, content, content_type)
    access_url = storage.get_file_url(object_key)

    return MediaUploadResponse(
        object_key=object_key,
        access_url=access_url,
    )


@router.post("/media/presigned-url", response_model=PresignedUrlResponse)
async def generate_presigned_url(request: PresignedUrlRequest):
    """Generate a presigned upload URL (for server-to-server or same-network use).

    NOTE: The presigned URL points to MinIO's internal Docker hostname.
    For external/browser uploads, use POST /api/media/upload instead.
    """
    storage = get_storage_service()
    if not storage:
        raise HTTPException(status_code=500, detail="Storage service unavailable")

    object_key = _build_object_key(request.category, request.entity_id, request.filename)

    upload_url = storage.get_presigned_upload_url(object_key)
    access_url = storage.get_file_url(object_key)

    return PresignedUrlResponse(
        upload_url=upload_url,
        object_key=object_key,
        access_url=access_url,
    )
