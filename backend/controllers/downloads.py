from typing import Optional
from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from backend.database import get_db
from backend.middlewares.auth import get_admin_or_nodal, get_optional_user
from backend.schemas.base.auth import UserDetails
from backend.services.downloads import DownloadsService, get_downloads_service
from backend.schemas.request.download import DownloadCreate, DownloadUpdate
from backend.schemas.response.download import DownloadResponse, DownloadsListResponse
from backend.meta import DownloadStatus
from backend.schemas.response.meta import SuccessResponse
from backend.services.audit import AuditService
from backend.meta.audit import AuditAction

router = APIRouter()
audit_service = AuditService()


@router.post("/downloads", response_model=DownloadResponse, status_code=201)
async def create_download(
    document_title: str = Form(...),
    document_type: str | None = Form(None),
    department_id: int | None = Form(None),
    description: str | None = Form(None),
    status: DownloadStatus | None = Form(DownloadStatus.ACTIVE),
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: UserDetails = Depends(get_admin_or_nodal),
    service: DownloadsService = Depends(get_downloads_service),
):
    payload = DownloadCreate(
        document_title=document_title,
        document_type=document_type,
        department_id=department_id,
        description=description,
        status=status,
    )
    response = await service.create_download(db, payload, file, current_user.user_id)
    await audit_service.log(
        db,
        "DOWNLOAD",
        AuditAction.CREATED,
        current_user.user_id,
        new_state=response.model_dump(mode="json") if hasattr(response, "model_dump") else None,
    )
    await db.commit()
    return response


@router.get("/downloads", response_model=DownloadsListResponse)
async def list_downloads(
    limit: int = 50,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
    user: Optional[UserDetails] = Depends(get_optional_user),
    service: DownloadsService = Depends(get_downloads_service),
):
    return await service.list_downloads(db, limit=limit, offset=offset, user=user)


@router.get("/downloads/{download_id}", response_model=DownloadResponse)
async def get_download(
    download_id: int,
    db: AsyncSession = Depends(get_db),
    user: Optional[UserDetails] = Depends(get_optional_user),
    service: DownloadsService = Depends(get_downloads_service),
):
    return await service.get_download(db, download_id, user=user)


@router.put("/downloads/{download_id}", response_model=DownloadResponse)
async def update_download(
    download_id: int,
    payload: DownloadUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: UserDetails = Depends(get_admin_or_nodal),
    service: DownloadsService = Depends(get_downloads_service),
):
    # Only superadmin can update
    response = await service.update_download(db, download_id, payload)
    await audit_service.log(
        db,
        "DOWNLOAD",
        AuditAction.CHANGED,
        current_user.user_id,
        new_state=response.model_dump(mode="json") if hasattr(response, "model_dump") else None,
    )
    await db.commit()
    return response


@router.delete("/downloads/{download_id}", response_model=SuccessResponse)
async def delete_download(
    download_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: UserDetails = Depends(get_admin_or_nodal),
    service: DownloadsService = Depends(get_downloads_service),
):
    ok = await service.delete_download(db, download_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Download not found")

    await audit_service.log(
        db,
        "DOWNLOAD",
        AuditAction.CHANGED,
        current_user.user_id,
        new_state={"id": download_id, "action": "deleted"},
    )
    await db.commit()
    return SuccessResponse(message="Download deleted successfully")
