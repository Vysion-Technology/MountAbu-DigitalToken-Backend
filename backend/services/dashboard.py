"""Dashboard service – assembles the citizen dashboard payload."""

from fastapi import Depends

from backend.dao.dashboard import DashboardDAO, get_dashboard_dao
from backend.schemas.response.dashboard import (
    CitizenDashboardResponse,
    CitizenOverviewStats,
    MaterialAvailableQuantity,
    MaterialUsageSummary,
    PhaseTokenUsage,
)
from backend.services.base import BaseService


class DashboardService(BaseService):
    """Assembles data from DashboardDAO into the citizen dashboard response."""

    def __init__(self, dao: DashboardDAO):
        self.dao = dao

    async def get_citizen_dashboard(self, user_id: int) -> CitizenDashboardResponse:
        """Build the full citizen dashboard response scoped to the given user."""

        app_counts = await self.dao.get_application_counts(user_id)
        complaint_counts = await self.dao.get_complaint_counts(user_id)
        material_usage_raw = await self.dao.get_material_usage(user_id)
        phase_usage = await self.dao.get_phase_token_usage(user_id)

        # Count issued tokens as sum of phases (phase-wise + renovation)
        tokens_issued = app_counts["tokens_issued"]

        overview = CitizenOverviewStats(
            total_applications=app_counts["total"],
            active_applications=app_counts["active"],
            tokens_issued=tokens_issued,
            total_complaints=complaint_counts["total"],
            closed_complaints=complaint_counts["closed"],
        )

        material_usage = [MaterialUsageSummary(**m) for m in material_usage_raw]

        available_quantity = [
            MaterialAvailableQuantity(
                material_id=m["material_id"],
                material_name=m["material_name"],
                unit=m["unit"],
                available_quantity=max(m["permitted_quantity"] - m["used_quantity"], 0),
            )
            for m in material_usage_raw
        ]

        return CitizenDashboardResponse(
            overview=overview,
            material_usage=material_usage,
            available_quantity=available_quantity,
            phase_token_usage=[PhaseTokenUsage(**p) for p in phase_usage],
        )


# ── Dependency injection ──────────────────────────────────────────────────────

async def get_dashboard_service(
    dao: DashboardDAO = Depends(get_dashboard_dao),
) -> DashboardService:
    """FastAPI dependency for DashboardService."""
    return DashboardService(dao)
