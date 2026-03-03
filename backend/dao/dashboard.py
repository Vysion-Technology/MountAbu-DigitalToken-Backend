"""Dashboard DAO – aggregation queries for citizen dashboard."""

from typing import Optional
from datetime import datetime
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

    # ── Reports & Analytics ───────────────────────────────────────────────

    async def get_reports_analytics(
        self,
        since: datetime,
        prev_start: datetime,
        prev_end: datetime,
        ward_id: Optional[int] = None,
        department_id: Optional[int] = None,
    ) -> dict:
        """Fetch all reports data: kpis, application_status, complaints_categories, and ward_activity."""

        # We reuse the logic required for AuthorityDashboard reports

        def _base_app_filter(stmt, dt_col=None, start=None, end=None):
            if ward_id:
                stmt = stmt.where(Application.ward_id == ward_id)
            if department_id:
                stmt = stmt.where(Application.department_id == department_id)
            if dt_col is not None and start is not None:
                stmt = stmt.where(dt_col >= start)
            if dt_col is not None and end is not None:
                stmt = stmt.where(dt_col < end)
            return stmt

        cur_total = (
            await self.session.execute(
                _base_app_filter(select(func.count(Application.id)))
            )
        ).scalar() or 0

        cur_approved = (
            await self.session.execute(
                _base_app_filter(
                    select(func.count(Application.id)).where(
                        Application.status.in_(
                            [
                                ApplicationStatus.APPROVED,
                                ApplicationStatus.TOKEN_GENERATED,
                            ]
                        )
                    )
                )
            )
        ).scalar() or 0

        cur_tokens = (
            await self.session.execute(
                _base_app_filter(
                    select(func.count(Application.id)).where(
                        Application.status == ApplicationStatus.TOKEN_GENERATED
                    )
                )
            )
        ).scalar() or 0

        def _complaint_filter(stmt, start=None, end=None):
            if ward_id:
                stmt = stmt.where(Complaint.ward_id == ward_id)
            if department_id:
                stmt = stmt.where(Complaint.department_id == department_id)
            if start:
                stmt = stmt.where(Complaint.created_at >= start)
            if end:
                stmt = stmt.where(Complaint.created_at < end)
            return stmt

        cur_complaints = (
            await self.session.execute(
                _complaint_filter(select(func.count(Complaint.id)))
            )
        ).scalar() or 0

        cur_closed = (
            await self.session.execute(
                _complaint_filter(
                    select(func.count(Complaint.id)).where(
                        Complaint.status == ComplaintStatus.RESOLVED
                    )
                )
            )
        ).scalar() or 0

        # Prev period
        from backend.dbmodels.application import ApplicationActionLog

        prev_actions = (
            select(ApplicationActionLog.application_id)
            .where(
                ApplicationActionLog.performed_at >= prev_start,
                ApplicationActionLog.performed_at < prev_end,
            )
            .distinct()
            .subquery()
        )
        prev_total = (
            await self.session.execute(select(func.count()).select_from(prev_actions))
        ).scalar() or 0

        prev_complaints = (
            await self.session.execute(
                _complaint_filter(
                    select(func.count(Complaint.id)), start=prev_start, end=prev_end
                )
            )
        ).scalar() or 0

        prev_closed = (
            await self.session.execute(
                _complaint_filter(
                    select(func.count(Complaint.id)).where(
                        Complaint.status == ComplaintStatus.RESOLVED
                    ),
                    start=prev_start,
                    end=prev_end,
                )
            )
        ).scalar() or 0

        def pct(cur, prev):
            if prev == 0:
                return None
            return round(((cur - prev) / prev) * 100, 1)

        kpis = [
            {
                "label": "Total Applications",
                "value": cur_total,
                "previous_value": prev_total,
                "percent_change": pct(cur_total, prev_total),
            },
            {
                "label": "Approved",
                "value": cur_approved,
                "previous_value": None,
                "percent_change": None,
            },
            {
                "label": "Tokens Issued",
                "value": cur_tokens,
                "previous_value": None,
                "percent_change": None,
            },
            {
                "label": "Complaints",
                "value": cur_complaints,
                "previous_value": prev_complaints,
                "percent_change": pct(cur_complaints, prev_complaints),
            },
            {
                "label": "Complaints Closed",
                "value": cur_closed,
                "previous_value": prev_closed,
                "percent_change": pct(cur_closed, prev_closed),
            },
        ]

        # Status counts
        stmt = select(Application.status, func.count(Application.id)).group_by(
            Application.status
        )
        if ward_id:
            stmt = stmt.where(Application.ward_id == ward_id)
        if department_id:
            stmt = stmt.where(Application.department_id == department_id)
        app_status_breakdown = [
            {"status": r[0].value, "count": r[1]}
            for r in (await self.session.execute(stmt)).all()
        ]

        # Category counts
        from backend.dbmodels.master import ComplaintCategory, Ward

        stmt = (
            select(
                ComplaintCategory.id, ComplaintCategory.name, func.count(Complaint.id)
            )
            .outerjoin(Complaint, Complaint.category_id == ComplaintCategory.id)
            .group_by(ComplaintCategory.id, ComplaintCategory.name)
            .order_by(func.count(Complaint.id).desc())
        )
        if ward_id:
            stmt = stmt.where(Complaint.ward_id == ward_id)
        if department_id:
            stmt = stmt.where(Complaint.department_id == department_id)
        cat_breakdown = [
            {"category_id": r[0], "category_name": r[1], "count": r[2]}
            for r in (await self.session.execute(stmt)).all()
            if r[2] > 0
        ]

        # Ward Activity
        app_sq = select(
            Application.ward_id,
            func.count(Application.id).label("applications"),
            func.count(
                case(
                    (
                        Application.status.in_(
                            [
                                ApplicationStatus.APPROVED,
                                ApplicationStatus.TOKEN_GENERATED,
                            ]
                        ),
                        Application.id,
                    )
                )
            ).label("approved"),
            func.count(
                case(
                    (
                        Application.status == ApplicationStatus.TOKEN_GENERATED,
                        Application.id,
                    )
                )
            ).label("tokens_issued"),
        ).group_by(Application.ward_id)
        if department_id:
            app_sq = app_sq.where(Application.department_id == department_id)
        app_sq = app_sq.subquery()

        comp_sq = select(
            Complaint.ward_id, func.count(Complaint.id).label("complaints")
        ).group_by(Complaint.ward_id)
        if department_id:
            comp_sq = comp_sq.where(Complaint.department_id == department_id)
        comp_sq = comp_sq.subquery()

        stmt = (
            select(
                Ward.id,
                Ward.name,
                func.coalesce(app_sq.c.applications, 0),
                func.coalesce(app_sq.c.approved, 0),
                func.coalesce(app_sq.c.tokens_issued, 0),
                func.coalesce(comp_sq.c.complaints, 0),
            )
            .outerjoin(app_sq, Ward.id == app_sq.c.ward_id)
            .outerjoin(comp_sq, Ward.id == comp_sq.c.ward_id)
            .order_by(Ward.name)
        )
        ward_activity = [
            {
                "ward_id": r[0],
                "ward_name": r[1],
                "applications": r[2],
                "approved": r[3],
                "tokens_issued": r[4],
                "complaints": r[5],
            }
            for r in (await self.session.execute(stmt)).all()
        ]

        return {
            "kpis": kpis,
            "application_status_breakdown": app_status_breakdown,
            "complaints_by_category": cat_breakdown,
            "ward_activity": ward_activity,
        }


# ── Dependency injection ──────────────────────────────────────────────────────


async def get_dashboard_dao(
    session: AsyncSession = Depends(get_db),
) -> DashboardDAO:
    """FastAPI dependency for DashboardDAO."""
    return DashboardDAO(session)
