from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Query
from fastapi.responses import StreamingResponse
from typing import Optional
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database import get_db
from backend.meta import MediaCategory, ApplicationDocumentType
from backend.middlewares.auth import get_current_user, get_current_user_id
from backend.schemas.base.auth import UserDetails
from backend.services.storage import get_storage_service, verify_download_token
from backend.schemas.request.complaint import PresignedUrlRequest
from backend.schemas.response.complaint import PresignedUrlResponse
from pydantic import BaseModel

# DB models – imported to validate entity existence and persist media records
from backend.dbmodels.application import Application, ApplicationDocument
from backend.dbmodels.complaint import Complaint, ComplaintMedia
from backend.dbmodels.notice import Notice
from backend.dbmodels.event import Event
from backend.dbmodels.tender import Tender
from backend.dbmodels.download import Download
from backend.dbmodels.leader import Leader

router = APIRouter()

# Maps MediaCategory → (DB model class, PK column)
_ENTITY_MODEL_MAP = {
    MediaCategory.APPLICATION: Application,
    MediaCategory.COMPLAINT: Complaint,
    MediaCategory.NOTICE: Notice,
    MediaCategory.EVENT: Event,
    MediaCategory.TENDER: Tender,
    MediaCategory.DOWNLOAD: Download,
    MediaCategory.LEADER: Leader,
}


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
    return f"{category.lower()}/{entity_part}/{clean_filename}"


async def _validate_entity_exists(
    db: AsyncSession,
    category: MediaCategory,
    entity_id: Optional[int],
) -> None:
    """Verify the referenced entity exists in the database.

    Raises HTTPException 404 if the entity cannot be found.
    GENERAL category skips validation (no entity association).
    """
    if category == MediaCategory.GENERAL:
        return  # No entity to validate

    if entity_id is None:
        raise HTTPException(
            status_code=400,
            detail=f"entity_id is required for category '{category.value}'",
        )

    model_cls = _ENTITY_MODEL_MAP.get(category)
    if model_cls is None:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown media category: {category.value}",
        )

    result = await db.execute(
        select(model_cls.id).where(model_cls.id == entity_id)
    )
    if result.scalar_one_or_none() is None:
        raise HTTPException(
            status_code=404,
            detail=f"{category.value} with id {entity_id} not found",
        )


async def _save_media_record(
    db: AsyncSession,
    category: MediaCategory,
    entity_id: Optional[int],
    object_key: str,
    content_type: str,
    filename: str,
    user_id: int,
    document_type: Optional[ApplicationDocumentType] = None,
) -> None:
    """Persist the upload in the appropriate entity-specific media table."""
    if category == MediaCategory.APPLICATION:
        doc = ApplicationDocument(
            application_id=entity_id,
            document_type=document_type or ApplicationDocumentType.OTHER,
            document_name=filename,
            document_path=object_key,
            document_by=user_id,
        )
        db.add(doc)

    elif category == MediaCategory.COMPLAINT:
        media = ComplaintMedia(
            complaint_id=entity_id,
            media_path=object_key,
            media_type=content_type,
            uploaded_by=user_id,
            is_initial=False,
        )
        db.add(media)

    # Categories that store the file path inline on the entity itself
    # (notices, events, tenders, downloads, leaders) don't have child
    # media tables yet.  The object_key is returned so callers can
    # link it manually.  Nothing to persist here for now.
    # GENERAL also has no entity, so nothing to persist.

    await db.commit()


@router.post("/media/upload", response_model=MediaUploadResponse)
async def upload_media(
    file: UploadFile = File(...),
    category: MediaCategory = Form(MediaCategory.APPLICATION),
    entity_id: Optional[int] = Form(None),
    document_type: Optional[ApplicationDocumentType] = Form(None),
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    """Upload a file directly through the backend (proxied to MinIO).

    The file is stored in MinIO **and** linked to the relevant database
    entity (application document, complaint media, etc.).
    """
    # TODO: Check that the current user is authorised to upload to this entity.
    #       e.g. citizens should only upload to their own applications/complaints;
    #       authority roles may upload to any entity they manage.

    # 1. Validate the referenced entity exists
    await _validate_entity_exists(db, category, entity_id)

    # 2. Upload to MinIO
    storage = get_storage_service()
    if not storage:
        raise HTTPException(status_code=500, detail="Storage service unavailable")

    object_key = _build_object_key(category.value, entity_id, file.filename)
    path = await storage.upload_file(file, object_key)
    
    # Use the magic-detected content type stored during validation
    content_type = getattr(file, "custom_mime_type", file.content_type or "application/octet-stream")

    # 3. Persist the media record in the database
    await _save_media_record(
        db,
        category,
        entity_id,
        object_key,
        content_type,
        file.filename,
        user_id,
        document_type=document_type,
    )

    access_url = storage.get_file_url(object_key)

    return MediaUploadResponse(
        object_key=object_key,
        access_url=access_url,
    )


@router.post("/media/presigned-url", response_model=PresignedUrlResponse)
async def generate_presigned_url(
    request: PresignedUrlRequest,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    """Generate a presigned upload URL (for server-to-server or same-network use).

    NOTE: The presigned URL points to MinIO's internal Docker hostname.
    For external/browser uploads, use POST /api/media/upload instead.
    """
    # TODO: Check that the current user is authorised to upload to this entity.

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


@router.get("/media/file/{file_path:path}")
async def download_file(
    file_path: str,
    token: str = Query(..., description="HMAC-signed download token"),
    expires: int = Query(..., description="Token expiry (unix timestamp)"),
):
    """Proxy file download from MinIO through the backend.

    URLs are generated by the backend with a signed token valid for 3 hours.
    No direct MinIO access is needed by clients.
    """
    if not verify_download_token(file_path, token, expires):
        raise HTTPException(status_code=403, detail="Invalid or expired download link")

    storage = get_storage_service()
    if not storage:
        raise HTTPException(status_code=500, detail="Storage service unavailable")

    try:
        response = storage.get_file_stream(file_path)
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"File not found: {e}")

    content_type = response.headers.get("Content-Type", "application/octet-stream")
    filename = file_path.rsplit("/", 1)[-1]

    return StreamingResponse(
        response,
        media_type=content_type,
        headers={
            "Content-Disposition": f'inline; filename="{filename}"',
            "X-Content-Type-Options": "nosniff",
        },
    )
