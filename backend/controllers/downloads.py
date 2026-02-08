from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from backend.database import get_db
from backend.core.dependencies import get_current_superadmin
from backend.dbmodels.user import User
from backend.services.downloads import DownloadsService, get_downloads_service
from backend.schemas.request.download import DownloadCreate, DownloadUpdate
from backend.schemas.response.download import DownloadResponse, DownloadsListResponse
from backend.schemas.response.meta import SuccessResponse

router = APIRouter()


@router.post("/downloads", response_model=DownloadResponse, status_code=201)
async def create_download(
    document_title: str = Form(...),
    document_type: str | None = Form(None),
    department_id: int | None = Form(None),
    description: str | None = Form(None),
    status: str | None = Form("ACTIVE"),
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_superadmin),
    service: DownloadsService = Depends(get_downloads_service),
):
    payload = DownloadCreate(
        document_title=document_title,
        document_type=document_type,
        department_id=department_id,
        description=description,
        status=status,
    )
    return await service.create_download(db, payload, file, current_user.id)


@router.get("/downloads", response_model=DownloadsListResponse)
async def list_downloads(limit: int = 50, offset: int = 0, db: AsyncSession = Depends(get_db), service: DownloadsService = Depends(get_downloads_service)):
    return await service.list_downloads(db, limit=limit, offset=offset)


@router.get("/downloads/{download_id}", response_model=DownloadResponse)
async def get_download(download_id: int, db: AsyncSession = Depends(get_db), service: DownloadsService = Depends(get_downloads_service)):
    return await service.get_download(db, download_id)


@router.put("/downloads/{download_id}", response_model=DownloadResponse)
async def update_download(
    download_id: int,
    payload: DownloadUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_superadmin),
    service: DownloadsService = Depends(get_downloads_service),
):
    # Only superadmin can update
    return await service.update_download(db, download_id, payload)


@router.delete("/downloads/{download_id}", response_model=SuccessResponse)
async def delete_download(
    download_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_superadmin),
    service: DownloadsService = Depends(get_downloads_service),
):
    ok = await service.delete_download(db, download_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Download not found")
    return SuccessResponse(message="Download deleted successfully")
