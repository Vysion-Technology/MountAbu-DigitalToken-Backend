"""Dashboard controller – citizen & authority endpoints."""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

from backend.core.dependencies import get_current_user
from backend.dbmodels.user import User
from backend.meta import UserRole
from backend.schemas.response.dashboard import CitizenDashboardResponse
from backend.schemas.response.authority_dashboard import AuthorityDashboardResponse
from backend.services.dashboard import DashboardService, get_dashboard_service
from backend.services.authority_dashboard import (
    AuthorityDashboardService,
    get_authority_dashboard_service,
)

router = APIRouter()

AUTHORITY_ROLES = {
    UserRole.SUPERADMIN,
    UserRole.NODAL_OFFICER,
    UserRole.COMMISSIONER,
    UserRole.JEN,
    UserRole.NAKA_INCHARGE,
    UserRole.DEPT_LAND,
    UserRole.DEPT_LEGAL,
    UserRole.DEPT_ATP,
}


# ── Citizen dashboard ─────────────────────────────────────────────────────────

@router.get("/dashboard/citizen", response_model=CitizenDashboardResponse)
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


# ── Authority dashboard ───────────────────────────────────────────────────────

@router.get("/dashboard/authority", response_model=AuthorityDashboardResponse)
async def get_authority_dashboard(
    days: int = Query(7, ge=1, le=365, description="Period in days for KPI comparison"),
    department_id: Optional[int] = Query(None, description="Filter by department"),
    ward_id: Optional[int] = Query(None, description="Filter by ward"),
    current_user: User = Depends(get_current_user),
    service: AuthorityDashboardService = Depends(get_authority_dashboard_service),
):
    """
    Return role-specific dashboard analytics for authority users.

    The response payload varies by role:
    - **Super Admin / Dept heads**: KPIs, application-status donut,
      complaints-by-category bar, ward-wise activity bar + table.
    - **JEN**: assigned/verified/pending KPIs, verification status,
      avg verification time trend, latest 5 applications.
    - **Naka Incharge**: total entries KPI, entries-by-naka bar,
      vehicle entry list.
    - **Commissioner (Complaint Officer)**: received/resolved/pending KPIs,
      complaints-by-category bar, resolution-status donut, complaint list.
    - **Nodal Officer**: tokens generated/utilized KPIs, token-status donut,
      material approved-vs-used bar, token utilization list.

    Query parameters ``days``, ``department_id``, ``ward_id`` apply to
    Super Admin / Dept-head dashboards only.
    """
    if current_user.role not in AUTHORITY_ROLES:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only authority users can access this dashboard",
        )

    return await service.get_dashboard(
        role=current_user.role,
        user_id=current_user.id,
        days=days,
        ward_id=ward_id,
        department_id=department_id,
    )
