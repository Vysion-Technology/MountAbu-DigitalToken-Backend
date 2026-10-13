from datetime import date
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database import get_db
from backend.middlewares.auth import get_current_user
from backend.schemas.base.auth import UserDetails
from backend.schemas.request.schedule import VehicleScheduleCreate
from backend.schemas.response.schedule import (
    AvailableSlotsResponse,
    VehicleScheduleResponse,
    TokenScheduleStatusResponse,
    CapacityHeatmapResponse,
)
from backend.services.schedule import VehicleScheduleService

router = APIRouter(prefix="/schedules", tags=["Vehicle Scheduling"])
schedule_service = VehicleScheduleService()


@router.get("/analytics/capacity-heatmap", response_model=CapacityHeatmapResponse)
async def get_capacity_heatmap(
    start_date: Optional[date] = Query(None, description="Start date (defaults to today)"),
    days: int = Query(14, ge=1, le=30, description="Number of days to project (1 to 30)"),
    db: AsyncSession = Depends(get_db),
    user: UserDetails = Depends(get_current_user),
) -> CapacityHeatmapResponse:
    """Get live capacity heatmap and booking load analytics across the next N days."""
    s_date = start_date or date.today()
    return await schedule_service.get_capacity_heatmap(db, s_date, days)


@router.get("/available-slots", response_model=AvailableSlotsResponse)

async def get_available_slots(
    date_val: date = Query(..., alias="date", description="Date to check available slots (YYYY-MM-DD)"),
    db: AsyncSession = Depends(get_db),
    user: UserDetails = Depends(get_current_user),
) -> AvailableSlotsResponse:
    """Get all slots and remaining vehicle capacities for the given date."""
    return await schedule_service.get_available_slots(db, date_val)


@router.post("", response_model=VehicleScheduleResponse, status_code=status.HTTP_201_CREATED)
async def book_vehicle_schedule(
    schedule_in: VehicleScheduleCreate,
    db: AsyncSession = Depends(get_db),
    user: UserDetails = Depends(get_current_user),
) -> VehicleScheduleResponse:
    """Book a vehicle schedule slot for an active token."""
    try:
        return await schedule_service.book_schedule(db, user.user_id, schedule_in)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/my-schedules", response_model=List[VehicleScheduleResponse])
async def get_my_schedules(
    db: AsyncSession = Depends(get_db),
    user: UserDetails = Depends(get_current_user),
) -> List[VehicleScheduleResponse]:
    """Get all vehicle schedules booked by current logged in citizen."""
    return await schedule_service.get_my_schedules(db, user.user_id)


@router.get("/by-token/{token_id}", response_model=TokenScheduleStatusResponse)
async def get_token_schedule_status(
    token_id: int,
    db: AsyncSession = Depends(get_db),
    user: UserDetails = Depends(get_current_user),
) -> TokenScheduleStatusResponse:
    """Check if an active vehicle schedule exists for a token."""
    return await schedule_service.get_token_schedule_status(db, token_id)


@router.get("/{schedule_id}", response_model=VehicleScheduleResponse)
async def get_schedule_details(
    schedule_id: int,
    db: AsyncSession = Depends(get_db),
    user: UserDetails = Depends(get_current_user),
) -> VehicleScheduleResponse:
    """Get vehicle schedule details by ID."""
    schedule = await schedule_service.get_schedule_by_id(db, schedule_id)
    if not schedule:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vehicle schedule not found")
    return schedule


@router.post("/{schedule_id}/cancel", response_model=VehicleScheduleResponse)
async def cancel_vehicle_schedule(
    schedule_id: int,
    db: AsyncSession = Depends(get_db),
    user: UserDetails = Depends(get_current_user),
) -> VehicleScheduleResponse:
    """Cancel a scheduled vehicle entry."""
    try:
        return await schedule_service.cancel_schedule(db, schedule_id, user.user_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
