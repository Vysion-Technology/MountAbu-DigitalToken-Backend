from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.ext.asyncio import AsyncSession
from backend.database import get_db
from backend.middlewares.auth import get_admin_or_nodal
from backend.schemas.base.auth import UserDetails
from backend.services.notices import NoticesService, get_notices_service
from backend.schemas.request.notice import NoticeCreate, NoticeUpdate
from backend.schemas.response.notice import NoticeResponse, NoticesListResponse
from backend.schemas.response.meta import SuccessResponse
from backend.meta import NoticeStatus, Visibility
from backend.services.audit import AuditService
from backend.meta.audit import AuditAction
from datetime import datetime

router = APIRouter()
audit_service = AuditService()


@router.post("/notices", response_model=NoticeResponse, status_code=201)
async def create_notice(
    title: str = Form(...),
    notice_type: str | None = Form(None),
    published_on: datetime | None = Form(None),
    valid_till: datetime | None = Form(None),
    status: NoticeStatus | None = Form(NoticeStatus.ACTIVE),
    visibility: Visibility | None = Form(Visibility.PUBLIC),
    image: UploadFile | None = File(None),
    document: UploadFile | None = File(None),
    db: AsyncSession = Depends(get_db),
    current_user: UserDetails = Depends(get_admin_or_nodal),
    service: NoticesService = Depends(get_notices_service),
):
    payload = NoticeCreate(
        title=title,
        notice_type=notice_type,
        published_on=published_on,
        valid_till=valid_till,
        status=status,
        visibility=visibility,
    )
    response = await service.create_notice(db, payload, current_user.user_id, image=image, document=document)
    await audit_service.log(
        db,
        "NOTICE",
        AuditAction.CREATED,
        current_user.user_id,
        new_state=response.model_dump(mode="json") if hasattr(response, "model_dump") else None,
    )
    await db.commit()
    return response


@router.get("/notices", response_model=NoticesListResponse)
async def list_notices(
    limit: int = 50,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
    service: NoticesService = Depends(get_notices_service),
):
    return await service.list_notices(db, limit=limit, offset=offset)


@router.get("/notices/{notice_id}", response_model=NoticeResponse)
async def get_notice(
    notice_id: int,
    db: AsyncSession = Depends(get_db),
    service: NoticesService = Depends(get_notices_service),
):
    return await service.get_notice(db, notice_id)


@router.put("/notices/{notice_id}", response_model=NoticeResponse)
async def update_notice(
    notice_id: int,
    payload: NoticeUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: UserDetails = Depends(get_admin_or_nodal),
    service: NoticesService = Depends(get_notices_service),
):
    response = await service.update_notice(db, notice_id, payload)
    await audit_service.log(
        db,
        "NOTICE",
        AuditAction.CHANGED,
        current_user.user_id,
        new_state=response.model_dump(mode="json") if hasattr(response, "model_dump") else None,
    )
    await db.commit()
    return response


@router.delete("/notices/{notice_id}", response_model=SuccessResponse)
async def delete_notice(
    notice_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: UserDetails = Depends(get_admin_or_nodal),
    service: NoticesService = Depends(get_notices_service),
):
    ok = await service.delete_notice(db, notice_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Notice not found")

    await audit_service.log(
        db,
        "NOTICE",
        AuditAction.CHANGED,
        current_user.user_id,
        new_state={"id": notice_id, "action": "deleted"},
    )
    await db.commit()
    return SuccessResponse(message="Notice deleted successfully")
