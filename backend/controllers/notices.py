from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from backend.database import get_db
from backend.core.dependencies import get_current_superadmin
from backend.dbmodels.user import User
from backend.services.notices import NoticesService, get_notices_service
from backend.schemas.request.notice import NoticeCreate, NoticeUpdate
from backend.schemas.response.notice import NoticeResponse, NoticesListResponse
from backend.schemas.response.meta import SuccessResponse

router = APIRouter()


@router.post("/notices", response_model=NoticeResponse, status_code=201)
async def create_notice(
    payload: NoticeCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_superadmin),
    service: NoticesService = Depends(get_notices_service),
):
    return await service.create_notice(db, payload, current_user.id)


@router.get("/notices", response_model=NoticesListResponse)
async def list_notices(limit: int = 50, offset: int = 0, db: AsyncSession = Depends(get_db), service: NoticesService = Depends(get_notices_service)):
    return await service.list_notices(db, limit=limit, offset=offset)


@router.get("/notices/{notice_id}", response_model=NoticeResponse)
async def get_notice(notice_id: int, db: AsyncSession = Depends(get_db), service: NoticesService = Depends(get_notices_service)):
    return await service.get_notice(db, notice_id)


@router.put("/notices/{notice_id}", response_model=NoticeResponse)
async def update_notice(
    notice_id: int,
    payload: NoticeUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_superadmin),
    service: NoticesService = Depends(get_notices_service),
):
    return await service.update_notice(db, notice_id, payload)


@router.delete("/notices/{notice_id}", response_model=SuccessResponse)
async def delete_notice(
    notice_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_superadmin),
    service: NoticesService = Depends(get_notices_service),
):
    ok = await service.delete_notice(db, notice_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Notice not found")
    return SuccessResponse(message="Notice deleted successfully")
