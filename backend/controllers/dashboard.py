"""Citizen dashboard controller."""

from fastapi import APIRouter, Depends

from backend.core.dependencies import get_current_user
from backend.dbmodels.user import User
from backend.schemas.response.dashboard import CitizenDashboardResponse
from backend.services.dashboard import DashboardService, get_dashboard_service

router = APIRouter()


@router.get("/dashboard", response_model=CitizenDashboardResponse)
async def get_citizen_dashboard(
    current_user: User = Depends(get_current_user),
    service: DashboardService = Depends(get_dashboard_service),
):
    """
    Return aggregated dashboard data for the logged-in citizen.

    Shows the user's own applications, complaints, material usage,
    and phase-wise token information.
    """
    return await service.get_citizen_dashboard(current_user.id)
