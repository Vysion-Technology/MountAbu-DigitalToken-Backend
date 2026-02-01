from fastapi import APIRouter, HTTPException
import uuid
from backend.services.storage import get_storage_service
from backend.schemas.request.complaint import PresignedUrlRequest
from backend.schemas.response.complaint import PresignedUrlResponse

router = APIRouter()

@router.post("/media/presigned-url", response_model=PresignedUrlResponse)
async def generate_presigned_url(request: PresignedUrlRequest):
    storage = get_storage_service()
    if not storage:
        raise HTTPException(status_code=500, detail="Storage service unavailable")

    # Generate path
    # If entity_id is provided, use it. Else use random UUID for temp/new item.
    if request.entity_id:
        entity_part = str(request.entity_id)
    else:
        entity_part = f"temp/{uuid.uuid4()}"
    
    # Sanitize filename simply
    clean_filename = request.filename.replace(" ", "_").replace("/", "").replace("\\", "")
    
    # Structure: category/id_or_temp/filename
    object_key = f"{request.category}/{entity_part}/{clean_filename}"
    
    upload_url = storage.get_presigned_upload_url(object_key)
    access_url = storage.get_file_url(object_key)
    
    return PresignedUrlResponse(
        upload_url=upload_url,
        object_key=object_key,
        access_url=access_url
    )
