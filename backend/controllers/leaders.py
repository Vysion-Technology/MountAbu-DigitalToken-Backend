from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from backend.database import get_db
from backend.middlewares.auth import get_admin_or_nodal
from backend.schemas.base.auth import UserDetails
from backend.services.leaders import LeadersService, get_leaders_service
from backend.schemas.request.leader import LeaderCreate, LeaderUpdate
from backend.schemas.response.leader import LeaderResponse, LeadersListResponse
from backend.schemas.response.meta import SuccessResponse

router = APIRouter()


@router.post("/leaders", response_model=LeaderResponse, status_code=201)
async def create_leader(
    payload: LeaderCreate,
    db: AsyncSession = Depends(get_db),
    current_user: UserDetails = Depends(get_admin_or_nodal),
    service: LeadersService = Depends(get_leaders_service),
):
    return await service.create_leader(db, payload, current_user.user_id)


@router.get("/leaders", response_model=LeadersListResponse)
async def list_leaders(
    limit: int = 50,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
    service: LeadersService = Depends(get_leaders_service),
):
    return await service.list_leaders(db, limit=limit, offset=offset)


@router.get("/leaders/{leader_id}", response_model=LeaderResponse)
async def get_leader(
    leader_id: int,
    db: AsyncSession = Depends(get_db),
    service: LeadersService = Depends(get_leaders_service),
):
    return await service.get_leader(db, leader_id)


@router.put("/leaders/{leader_id}", response_model=LeaderResponse)
async def update_leader(
    leader_id: int,
    payload: LeaderUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: UserDetails = Depends(get_admin_or_nodal),
    service: LeadersService = Depends(get_leaders_service),
):
    return await service.update_leader(db, leader_id, payload)


@router.delete("/leaders/{leader_id}", response_model=SuccessResponse)
async def delete_leader(
    leader_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: UserDetails = Depends(get_admin_or_nodal),
    service: LeadersService = Depends(get_leaders_service),
):
    ok = await service.delete_leader(db, leader_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Leader not found")
    return SuccessResponse(message="Leader deleted successfully")
