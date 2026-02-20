"""Dashboard DAO – aggregation queries for citizen dashboard."""

from fastapi import Depends
from sqlalchemy import func, select, case
from sqlalchemy.ext.asyncio import AsyncSession

from backend.dao.base import BaseDAO
from backend.database import get_db
from backend.dbmodels.application import (
    Application,
    ApplicationPhaseMaterial,
    ApprovedApplicationPhase,
    Material,
    VehicleEntry,
    VehicleMaterial,
)
from backend.dbmodels.complaint import Complaint
from backend.meta import (
    ApplicationStatus,
    ComplaintStatus,
)


class DashboardDAO(BaseDAO):
    """Aggregation queries powering the citizen dashboard (scoped to a single user)."""

    # ── Overview stats ────────────────────────────────────────────────────

    async def get_application_counts(self, user_id: int) -> dict:
        """Total / active / tokens-issued counts for this citizen's applications."""
        active_statuses = [
            ApplicationStatus.PENDING,
            ApplicationStatus.SUBMITTED,
            ApplicationStatus.FORWARDED,
            ApplicationStatus.WITHHELD,
            ApplicationStatus.OBJECTED,
            ApplicationStatus.APPROVED,
        ]
        stmt = select(
            func.count(Application.id).label("total"),
            func.count(
                case((Application.status.in_(active_statuses), Application.id))
            ).label("active"),
            func.count(
                case(
                    (
                        Application.status == ApplicationStatus.TOKEN_GENERATED,
                        Application.id,
                    )
                )
            ).label("tokens_issued"),
        ).where(Application.user_id == user_id)
        row = (await self.session.execute(stmt)).one()
        return {
            "total": row.total,
            "active": row.active,
            "tokens_issued": row.tokens_issued,
        }

    async def get_complaint_counts(self, user_id: int) -> dict:
        """Total / closed complaint counts for this citizen."""
        stmt = select(
            func.count(Complaint.id).label("total"),
            func.count(
                case((Complaint.status == ComplaintStatus.RESOLVED, Complaint.id))
            ).label("closed"),
        ).where(Complaint.user_id == user_id)
        row = (await self.session.execute(stmt)).one()
        return {"total": row.total, "closed": row.closed}

    # ── Material usage ────────────────────────────────────────────────────

    async def get_material_usage(self, user_id: int) -> list[dict]:
        """Permitted vs used quantities per material for this citizen's apps."""

        # IDs of the citizen's applications
        user_apps = (
            select(Application.id)
            .where(Application.user_id == user_id)
            .subquery("user_apps")
        )

        # Total permitted per material
        permitted_sq = (
            select(
                ApplicationPhaseMaterial.material_id,
                func.coalesce(func.sum(ApplicationPhaseMaterial.quantity), 0).label(
                    "permitted"
                ),
            )
            .where(ApplicationPhaseMaterial.application_id.in_(select(user_apps.c.id)))
            .group_by(ApplicationPhaseMaterial.material_id)
            .subquery("permitted_sq")
        )

        # Total used per material (naka entries)
        used_sq = (
            select(
                VehicleMaterial.material_id,
                func.coalesce(func.sum(VehicleMaterial.quantity), 0).label("used"),
            )
            .join(VehicleEntry, VehicleMaterial.vehicle_entry_id == VehicleEntry.id)
            .where(VehicleEntry.application_id.in_(select(user_apps.c.id)))
            .group_by(VehicleMaterial.material_id)
            .subquery("used_sq")
        )

        stmt = (
            select(
                Material.id.label("material_id"),
                Material.name.label("material_name"),
                Material.unit.label("unit"),
                func.coalesce(permitted_sq.c.permitted, 0).label("permitted"),
                func.coalesce(used_sq.c.used, 0).label("used"),
            )
            .outerjoin(permitted_sq, Material.id == permitted_sq.c.material_id)
            .outerjoin(used_sq, Material.id == used_sq.c.material_id)
            .where(
                (permitted_sq.c.permitted.isnot(None)) | (used_sq.c.used.isnot(None))
            )
            .order_by(Material.name)
        )

        rows = (await self.session.execute(stmt)).all()
        results = []
        for r in rows:
            permitted = r.permitted or 0
            used = r.used or 0
            pct = round((used / permitted) * 100, 1) if permitted > 0 else 0.0
            results.append(
                {
                    "material_id": r.material_id,
                    "material_name": r.material_name,
                    "unit": r.unit,
                    "permitted_quantity": permitted,
                    "used_quantity": used,
                    "usage_percent": pct,
                }
            )
        return results

    # ── Phase-wise token usage ────────────────────────────────────────────

    async def get_phase_token_usage(self, user_id: int) -> list[dict]:
        """Count of phases grouped by phase status for this citizen's apps."""
        user_apps = (
            select(Application.id)
            .where(Application.user_id == user_id)
            .subquery("user_apps")
        )

        stmt = (
            select(
                ApprovedApplicationPhase.status.label("phase_status"),
                func.count(ApprovedApplicationPhase.id).label("count"),
            )
            .where(ApprovedApplicationPhase.application_id.in_(select(user_apps.c.id)))
            .group_by(ApprovedApplicationPhase.status)
            .order_by(func.count(ApprovedApplicationPhase.id).desc())
        )
        rows = (await self.session.execute(stmt)).all()
        return [{"phase_status": r.phase_status.value, "count": r.count} for r in rows]


# ── Dependency injection ──────────────────────────────────────────────────────


async def get_dashboard_dao(
    session: AsyncSession = Depends(get_db),
) -> DashboardDAO:
    """FastAPI dependency for DashboardDAO."""
    return DashboardDAO(session)
