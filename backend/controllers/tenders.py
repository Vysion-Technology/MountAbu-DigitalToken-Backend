from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.ext.asyncio import AsyncSession
from backend.database import get_db
from backend.middlewares.auth import get_admin_or_nodal
from backend.schemas.base.auth import UserDetails
from backend.services.tenders import TendersService, get_tenders_service
from backend.schemas.request.tender import TenderCreate, TenderUpdate
from backend.schemas.response.tender import TenderResponse, TendersListResponse
from backend.schemas.response.meta import SuccessResponse
from backend.meta import TenderStatus
from backend.services.audit import AuditService
from backend.meta.audit import AuditAction
from datetime import datetime

router = APIRouter()
audit_service = AuditService()


@router.post("/tenders", response_model=TenderResponse, status_code=201)
async def create_tender(
    title: str = Form(...),
    tender_type: str | None = Form(None),
    department_id: int | None = Form(None),
    amount: float | None = Form(None),
    published_on: datetime | None = Form(None),
    submission_deadline: datetime | None = Form(None),
    status: TenderStatus | None = Form(TenderStatus.ACTIVE),
    document: UploadFile | None = File(None),
    db: AsyncSession = Depends(get_db),
    current_user: UserDetails = Depends(get_admin_or_nodal),
    service: TendersService = Depends(get_tenders_service),
):
    payload = TenderCreate(
        title=title,
        tender_type=tender_type,
        department_id=department_id,
        amount=amount,
        published_on=published_on,
        submission_deadline=submission_deadline,
        status=status,
    )
    response = await service.create_tender(db, payload, current_user.user_id, document=document)
    await audit_service.log(
        db,
        "TENDER",
        AuditAction.CREATED,
        current_user.user_id,
        new_state=response.model_dump(mode="json") if hasattr(response, "model_dump") else None,
    )
    await db.commit()
    return response


@router.get("/tenders", response_model=TendersListResponse)
async def list_tenders(
    limit: int = 50,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
    service: TendersService = Depends(get_tenders_service),
):
    return await service.list_tenders(db, limit=limit, offset=offset)


@router.get("/tenders/{tender_id}", response_model=TenderResponse)
async def get_tender(
    tender_id: int,
    db: AsyncSession = Depends(get_db),
    service: TendersService = Depends(get_tenders_service),
):
    return await service.get_tender(db, tender_id)


@router.put("/tenders/{tender_id}", response_model=TenderResponse)
async def update_tender(
    tender_id: int,
    title: str | None = Form(None),
    tender_type: str | None = Form(None),
    department_id: int | None = Form(None),
    amount: float | None = Form(None),
    published_on: datetime | None = Form(None),
    submission_deadline: datetime | None = Form(None),
    status: TenderStatus | None = Form(None),
    document: UploadFile | None = File(None),
    db: AsyncSession = Depends(get_db),
    current_user: UserDetails = Depends(get_admin_or_nodal),
    service: TendersService = Depends(get_tenders_service),
):
    payload = TenderUpdate(
        title=title,
        tender_type=tender_type,
        department_id=department_id,
        amount=amount,
        published_on=published_on,
        submission_deadline=submission_deadline,
        status=status,
    )
    response = await service.update_tender(db, tender_id, payload, document=document)
    await audit_service.log(
        db,
        "TENDER",
        AuditAction.CHANGED,
        current_user.user_id,
        new_state=response.model_dump(mode="json") if hasattr(response, "model_dump") else None,
    )
    await db.commit()
    return response


@router.delete("/tenders/{tender_id}", response_model=SuccessResponse)
async def delete_tender(
    tender_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: UserDetails = Depends(get_admin_or_nodal),
    service: TendersService = Depends(get_tenders_service),
):
    ok = await service.delete_tender(db, tender_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Tender not found")

    await audit_service.log(
        db,
        "TENDER",
        AuditAction.CHANGED,
        current_user.user_id,
        new_state={"id": tender_id, "action": "deleted"},
    )
    await db.commit()
    return SuccessResponse(message="Tender deleted successfully")
