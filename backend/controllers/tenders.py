from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from backend.database import get_db
from backend.core.dependencies import get_current_superadmin
from backend.dbmodels.user import User
from backend.services.tenders import TendersService, get_tenders_service
from backend.schemas.request.tender import TenderCreate, TenderUpdate
from backend.schemas.response.tender import TenderResponse, TendersListResponse
from backend.schemas.response.meta import SuccessResponse

router = APIRouter()


@router.post("/tenders", response_model=TenderResponse, status_code=201)
async def create_tender(
    payload: TenderCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_superadmin),
    service: TendersService = Depends(get_tenders_service),
):
    return await service.create_tender(db, payload, current_user.id)


@router.get("/tenders", response_model=TendersListResponse)
async def list_tenders(limit: int = 50, offset: int = 0, db: AsyncSession = Depends(get_db), service: TendersService = Depends(get_tenders_service)):
    return await service.list_tenders(db, limit=limit, offset=offset)


@router.get("/tenders/{tender_id}", response_model=TenderResponse)
async def get_tender(tender_id: int, db: AsyncSession = Depends(get_db), service: TendersService = Depends(get_tenders_service)):
    return await service.get_tender(db, tender_id)


@router.put("/tenders/{tender_id}", response_model=TenderResponse)
async def update_tender(
    tender_id: int,
    payload: TenderUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_superadmin),
    service: TendersService = Depends(get_tenders_service),
):
    return await service.update_tender(db, tender_id, payload)


@router.delete("/tenders/{tender_id}", response_model=SuccessResponse)
async def delete_tender(
    tender_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_superadmin),
    service: TendersService = Depends(get_tenders_service),
):
    ok = await service.delete_tender(db, tender_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Tender not found")
    return SuccessResponse(message="Tender deleted successfully")