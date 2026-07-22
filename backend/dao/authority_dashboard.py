"""Authority dashboard DAO – role-specific aggregation queries."""

from datetime import datetime, timedelta
from typing import Optional

from fastapi import Depends
from sqlalchemy import func, select, case, and_
from sqlalchemy.ext.asyncio import AsyncSession

from backend.dao.base import BaseDAO
from backend.database import get_db
from backend.dbmodels.application import (
    Application,
    ApplicationActionLog,
    ApplicationPhaseMaterial,
    ApprovedApplicationPhase,
    InspectionReport,
    Material,
    VehicleEntry as NakaEntry,
    VehicleMaterial,
)
from backend.dbmodels.complaint import Complaint
from backend.dbmodels.master import ComplaintCategory, Ward
from backend.dbmodels.user import User
from backend.meta import (
    ApplicationPhaseStatus,
    ApplicationStatus,
    ApplicationType,
    ComplaintStatus,
)


class AuthorityDashboardDAO(BaseDAO):
    """Aggregation queries powering role-specific authority dashboards."""

    # ─────────────────────────────────────────────────────────────────────────
    # SUPER ADMIN
    # ─────────────────────────────────────────────────────────────────────────

    async def superadmin_kpis(
        self,
        since: datetime,
        prev_start: datetime,
        prev_end: datetime,
        ward_id: Optional[int] = None,
        department_id: Optional[int] = None,
    ) -> list[dict]:
        """KPI cards with period-over-period % change."""

        def _base_app_filter(stmt, dt_col=None, start=None, end=None):
            if ward_id:
                stmt = stmt.where(Application.ward_id == ward_id)
            if department_id:
                stmt = stmt.where(Application.department_id == department_id)
            if dt_col is not None:
                if start is not None and end is not None:
                    stmt = stmt.where(and_(dt_col >= start, dt_col < end))
                elif start is not None:
                    stmt = stmt.where(dt_col >= start)
                elif end is not None:
                    stmt = stmt.where(dt_col < end)
            return stmt

        # --- Current period counts
        cur_total = (
            await self.session.execute(
                _base_app_filter(
                    select(func.count(Application.id)),
                    dt_col=Application.created_at,
                    start=since,
                )
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
                    ),
                    dt_col=Application.created_at,
                    start=since,
                )
            )
        ).scalar() or 0

        cur_tokens = (
            await self.session.execute(
                _base_app_filter(
                    select(func.count(Application.id)).where(
                        Application.status == ApplicationStatus.TOKEN_GENERATED
                    ),
                    dt_col=Application.created_at,
                    start=since,
                )
            )
        ).scalar() or 0

        # Complaints
        def _complaint_filter(stmt, start=None, end=None):
            if ward_id:
                stmt = stmt.where(Complaint.ward_id == ward_id)
            if department_id:
                stmt = stmt.join(
                    ComplaintCategory, Complaint.category_id == ComplaintCategory.id
                ).where(ComplaintCategory.department_id == department_id)
            if start:
                stmt = stmt.where(Complaint.created_at >= start)
            if end:
                stmt = stmt.where(Complaint.created_at < end)
            return stmt

        cur_complaints = (
            await self.session.execute(
                _complaint_filter(select(func.count(Complaint.id)), start=since)
            )
        ).scalar() or 0

        cur_closed = (
            await self.session.execute(
                _complaint_filter(
                    select(func.count(Complaint.id)).where(
                        Complaint.status == ComplaintStatus.RESOLVED
                    ),
                    start=since,
                )
            )
        ).scalar() or 0

        # Previous-period counts
        prev_total = (
            await self.session.execute(
                _base_app_filter(
                    select(func.count(Application.id)),
                    dt_col=Application.created_at,
                    start=prev_start,
                    end=prev_end,
                )
            )
        ).scalar() or 0

        prev_complaints = (
            await self.session.execute(
                _complaint_filter(
                    select(func.count(Complaint.id)),
                    start=prev_start,
                    end=prev_end,
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

        return [
            {
                "label": "Total Applications",
                "value": cur_total,
                "previous_value": prev_total,
                "percent_change": pct(cur_total, prev_total),
            },
            {
                "label": "Applications Approved",
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
                "label": "Total Complaints",
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

    async def application_status_breakdown(
        self,
        since: Optional[datetime] = None,
        ward_id: Optional[int] = None,
        department_id: Optional[int] = None,
    ) -> list[dict]:
        stmt = select(
            Application.status, func.count(Application.id).label("count")
        ).group_by(Application.status)
        if since:
            stmt = stmt.where(Application.created_at >= since)
        if ward_id:
            stmt = stmt.where(Application.ward_id == ward_id)
        if department_id:
            stmt = stmt.where(Application.department_id == department_id)
        rows = (await self.session.execute(stmt)).all()
        return [{"status": r[0].value, "count": r[1]} for r in rows]

    async def complaints_by_category(
        self,
        since: Optional[datetime] = None,
        ward_id: Optional[int] = None,
        department_id: Optional[int] = None,
        assigned_to_id: Optional[int] = None,
    ) -> list[dict]:
        stmt = (
            select(
                ComplaintCategory.id,
                ComplaintCategory.name,
                func.count(Complaint.id).label("count"),
            )
            .outerjoin(Complaint, Complaint.category_id == ComplaintCategory.id)
            .group_by(ComplaintCategory.id, ComplaintCategory.name)
            .order_by(func.count(Complaint.id).desc())
        )
        if since:
            stmt = stmt.where(Complaint.created_at >= since)
        if ward_id:
            stmt = stmt.where(Complaint.ward_id == ward_id)
        if department_id:
            stmt = stmt.where(ComplaintCategory.department_id == department_id)
        if assigned_to_id:
            stmt = stmt.where(Complaint.assigned_to_id == assigned_to_id)
        rows = (await self.session.execute(stmt)).all()
        return [
            {"category_id": r[0], "category_name": r[1], "count": r[2]}
            for r in rows
            if r[2] > 0
        ]

    async def ward_activity(
        self, since: Optional[datetime] = None, department_id: Optional[int] = None
    ) -> list[dict]:
        """Per-ward counts: applications, approved, tokens, complaints."""
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
        if since:
            app_sq = app_sq.where(Application.created_at >= since)
        if department_id:
            app_sq = app_sq.where(Application.department_id == department_id)
        app_sq = app_sq.subquery()

        comp_sq = select(
            Complaint.ward_id,
            func.count(Complaint.id).label("complaints"),
        ).group_by(Complaint.ward_id)
        if since:
            comp_sq = comp_sq.where(Complaint.created_at >= since)
        if department_id:
            comp_sq = comp_sq.join(
                ComplaintCategory, Complaint.category_id == ComplaintCategory.id
            ).where(ComplaintCategory.department_id == department_id)
        comp_sq = comp_sq.subquery()

        stmt = (
            select(
                Ward.id,
                Ward.name,
                func.coalesce(app_sq.c.applications, 0).label("applications"),
                func.coalesce(app_sq.c.approved, 0).label("approved"),
                func.coalesce(app_sq.c.tokens_issued, 0).label("tokens_issued"),
                func.coalesce(comp_sq.c.complaints, 0).label("complaints"),
            )
            .outerjoin(app_sq, Ward.id == app_sq.c.ward_id)
            .outerjoin(comp_sq, Ward.id == comp_sq.c.ward_id)
            .order_by(Ward.name)
        )
        rows = (await self.session.execute(stmt)).all()
        return [
            {
                "ward_id": r[0],
                "ward_name": r[1],
                "applications": r[2],
                "approved": r[3],
                "tokens_issued": r[4],
                "complaints": r[5],
            }
            for r in rows
        ]

    # ─────────────────────────────────────────────────────────────────────────
    # JEN
    # ─────────────────────────────────────────────────────────────────────────

    async def jen_kpis(
        self,
        user_id: int,
        since: Optional[datetime] = None,
        ward_id: Optional[int] = None,
    ) -> list[dict]:
        """Assigned / verified / pending for this JEN user."""
        verified_stmt = select(func.count(InspectionReport.id)).where(
            InspectionReport.inspected_by == user_id
        )
        if since:
            verified_stmt = verified_stmt.where(InspectionReport.inspected_at >= since)

        verified = (await self.session.execute(verified_stmt)).scalar() or 0

        # Apps needing JEN inspection
        pending_sq = select(func.count(Application.id)).where(
            Application.status == ApplicationStatus.APPROVED,
            Application.type == ApplicationType.NEW,
            ~Application.id.in_(
                select(InspectionReport.application_id).where(
                    InspectionReport.inspected_by == user_id
                )
            ),
        )
        if since:
            pending_sq = pending_sq.where(Application.created_at >= since)
        if ward_id:
            pending_sq = pending_sq.where(Application.ward_id == ward_id)

        pending = (await self.session.execute(pending_sq)).scalar() or 0

        assigned = verified + pending
        return [
            {
                "label": "Applications Assigned",
                "value": assigned,
                "previous_value": None,
                "percent_change": None,
            },
            {
                "label": "Applications Verified",
                "value": verified,
                "previous_value": None,
                "percent_change": None,
            },
            {
                "label": "Applications Pending",
                "value": pending,
                "previous_value": None,
                "percent_change": None,
            },
        ]

    async def jen_verification_status(
        self,
        user_id: int,
        since: Optional[datetime] = None,
        ward_id: Optional[int] = None,
    ) -> list[dict]:
        """Verification status breakdown – approved vs pending apps for JEN."""
        inspected_ids = select(InspectionReport.application_id).where(
            InspectionReport.inspected_by == user_id
        )
        if since:
            inspected_ids = inspected_ids.where(InspectionReport.inspected_at >= since)

        # Inspected
        inspected_count_stmt = select(func.count()).select_from(
            inspected_ids.distinct().subquery()
        )
        inspected_count = (await self.session.execute(inspected_count_stmt)).scalar() or 0

        # Pending inspection
        pending_stmt = select(func.count(Application.id)).where(
            Application.status == ApplicationStatus.APPROVED,
            Application.type == ApplicationType.NEW,
            ~Application.id.in_(inspected_ids),
        )
        if since:
            pending_stmt = pending_stmt.where(Application.created_at >= since)
        if ward_id:
            pending_stmt = pending_stmt.where(Application.ward_id == ward_id)

        pending_count = (await self.session.execute(pending_stmt)).scalar() or 0

        return [
            {"status": "Inspected", "count": inspected_count},
            {"status": "Pending", "count": pending_count},
        ]

    async def jen_avg_verification_trend(self, user_id: int, days: int) -> list[dict]:
        """Daily average inspection turnaround (hours) over the last N days."""
        since = datetime.now() - timedelta(days=days)
        stmt = (
            select(
                func.date(InspectionReport.inspected_at).label("day"),
                func.avg(
                    func.extract(
                        "epoch",
                        InspectionReport.inspected_at
                        - (
                            select(func.min(ApplicationActionLog.performed_at))
                            .where(
                                ApplicationActionLog.application_id
                                == InspectionReport.application_id
                            )
                            .correlate(InspectionReport)
                            .scalar_subquery()
                        ),
                    )
                    / 3600
                ).label("avg_hours"),
            )
            .where(
                InspectionReport.inspected_by == user_id,
                InspectionReport.inspected_at >= since,
            )
            .group_by(func.date(InspectionReport.inspected_at))
            .order_by(func.date(InspectionReport.inspected_at))
        )
        rows = (await self.session.execute(stmt)).all()
        return [
            {"period": str(r[0]), "avg_hours": round(float(r[1] or 0), 1)} for r in rows
        ]

    async def jen_latest_applications(
        self,
        user_id: int,
        limit: int = 5,
        ward_id: Optional[int] = None,
    ) -> list[dict]:
        """Latest applications relevant to JEN (inspected or pending)."""
        inspected_ids = select(InspectionReport.application_id).where(
            InspectionReport.inspected_by == user_id
        )

        stmt = select(Application).where(
            (Application.id.in_(inspected_ids))
            | (
                and_(
                    Application.status == ApplicationStatus.APPROVED,
                    Application.type == ApplicationType.NEW,
                )
            )
        )

        if ward_id:
            stmt = stmt.where(Application.ward_id == ward_id)

        stmt = stmt.order_by(Application.id.desc()).limit(limit)

        rows = (await self.session.execute(stmt)).scalars().all()

        # Check which ones have inspection by this JEN
        inspected_set_result = await self.session.execute(inspected_ids)
        inspected_set = {r[0] for r in inspected_set_result.all()}

        return [
            {
                "application_id": a.id,
                "applicant_name": a.applicant_name,
                "application_type": a.type.value,
                "status": a.status.value,
                "inspected": a.id in inspected_set,
            }
            for a in rows
        ]

    # ─────────────────────────────────────────────────────────────────────────
    # NAKA INCHARGE
    # ─────────────────────────────────────────────────────────────────────────

    async def naka_kpis(self, user_id: int, since: Optional[datetime] = None) -> list[dict]:
        stmt = select(func.count(NakaEntry.id)).where(NakaEntry.entry_by == user_id)
        if since:
            stmt = stmt.where(NakaEntry.entry_at >= since)

        total = (await self.session.execute(stmt)).scalar() or 0
        return [
            {
                "label": "Total Vehicle Entries",
                "value": total,
                "previous_value": None,
                "percent_change": None,
            },
        ]

    async def naka_entries_by_user(self, since: Optional[datetime] = None) -> list[dict]:
        """Entry count per naka incharge user (for bar chart)."""
        stmt = (
            select(
                NakaEntry.entry_by,
                User.name,
                func.count(NakaEntry.id).label("entry_count"),
            )
            .join(User, NakaEntry.entry_by == User.id)
            .group_by(NakaEntry.entry_by, User.name)
            .order_by(func.count(NakaEntry.id).desc())
        )
        if since:
            stmt = stmt.where(NakaEntry.entry_at >= since)

        rows = (await self.session.execute(stmt)).all()
        return [{"user_id": r[0], "user_name": r[1], "entry_count": r[2]} for r in rows]

    async def naka_vehicle_entry_list(
        self, user_id: int, limit: int = 20, since: Optional[datetime] = None
    ) -> list[dict]:
        """Recent vehicle entries by this naka user."""
        stmt = (
            select(
                NakaEntry,
                Material.name.label("material_name"),
                VehicleMaterial.quantity.label("quantity_brought"),
            )
            .join(VehicleMaterial, VehicleMaterial.vehicle_entry_id == NakaEntry.id)
            .join(Material, VehicleMaterial.material_id == Material.id)
            .where(NakaEntry.entry_by == user_id)
            .order_by(NakaEntry.entry_at.desc())
            .limit(limit)
        )
        if since:
            stmt = stmt.where(NakaEntry.entry_at >= since)

        rows = (await self.session.execute(stmt)).all()
        return [
            {
                "naka_entry_id": r[0].id,
                "application_id": r[0].application_id,
                "vehicle_number": r[0].vehicle_number,
                "material_name": r[1],
                "quantity_brought": r[2],
                "entry_at": r[0].entry_at.isoformat() if r[0].entry_at else None,
            }
            for r in rows
        ]

    # ─────────────────────────────────────────────────────────────────────────
    # COMPLAINT OFFICER (COMMISSIONER)
    # ─────────────────────────────────────────────────────────────────────────

    async def complaint_officer_kpis(
        self,
        since: Optional[datetime] = None,
        ward_id: Optional[int] = None,
        assigned_to_id: Optional[int] = None,
    ) -> list[dict]:
        def _filter(stmt):
            if since:
                stmt = stmt.where(Complaint.created_at >= since)
            if ward_id:
                stmt = stmt.where(Complaint.ward_id == ward_id)
            if assigned_to_id:
                stmt = stmt.where(Complaint.assigned_to_id == assigned_to_id)
            return stmt

        received = (
            await self.session.execute(_filter(select(func.count(Complaint.id))))
        ).scalar() or 0

        resolved = (
            await self.session.execute(
                _filter(
                    select(func.count(Complaint.id)).where(
                        Complaint.status == ComplaintStatus.RESOLVED
                    )
                )
            )
        ).scalar() or 0

        pending = (
            await self.session.execute(
                _filter(
                    select(func.count(Complaint.id)).where(
                        Complaint.status.in_(
                            [
                                ComplaintStatus.PENDING,
                                ComplaintStatus.IN_PROGRESS,
                            ]
                        )
                    )
                )
            )
        ).scalar() or 0

        return [
            {
                "label": "Complaints Received",
                "value": received,
                "previous_value": None,
                "percent_change": None,
            },
            {
                "label": "Complaints Resolved",
                "value": resolved,
                "previous_value": None,
                "percent_change": None,
            },
            {
                "label": "Complaints Pending",
                "value": pending,
                "previous_value": None,
                "percent_change": None,
            },
        ]

    async def complaint_resolution_status(
        self,
        since: Optional[datetime] = None,
        ward_id: Optional[int] = None,
        assigned_to_id: Optional[int] = None,
    ) -> list[dict]:
        stmt = select(
            Complaint.status, func.count(Complaint.id).label("count")
        ).group_by(Complaint.status)
        if since:
            stmt = stmt.where(Complaint.created_at >= since)
        if ward_id:
            stmt = stmt.where(Complaint.ward_id == ward_id)
        if assigned_to_id:
            stmt = stmt.where(Complaint.assigned_to_id == assigned_to_id)

        rows = (await self.session.execute(stmt)).all()
        return [{"status": r[0].value, "count": r[1]} for r in rows]

    async def complaint_list(
        self,
        limit: int = 20,
        since: Optional[datetime] = None,
        ward_id: Optional[int] = None,
        assigned_to_id: Optional[int] = None,
    ) -> list[dict]:
        stmt = (
            select(Complaint, ComplaintCategory.name.label("category_name"))
            .outerjoin(ComplaintCategory, Complaint.category_id == ComplaintCategory.id)
            .order_by(Complaint.created_at.desc())
            .limit(limit)
        )
        if since:
            stmt = stmt.where(Complaint.created_at >= since)
        if ward_id:
            stmt = stmt.where(Complaint.ward_id == ward_id)
        if assigned_to_id:
            stmt = stmt.where(Complaint.assigned_to_id == assigned_to_id)

        rows = (await self.session.execute(stmt)).all()
        return [
            {
                "complaint_id": r[0].id,
                "title": r[0].title,
                "category_name": r[1],
                "status": r[0].status.value,
                "applicant_name": r[0].applicant_name,
                "created_at": r[0].created_at.isoformat() if r[0].created_at else None,
            }
            for r in rows
        ]

    # ─────────────────────────────────────────────────────────────────────────
    # NODAL OFFICER
    # ─────────────────────────────────────────────────────────────────────────

    async def nodal_kpis(self, since: Optional[datetime] = None) -> list[dict]:
        gen_stmt = select(func.count(Application.id)).where(
            Application.status == ApplicationStatus.TOKEN_GENERATED
        )
        util_stmt = select(func.count(ApprovedApplicationPhase.id)).where(
            ApprovedApplicationPhase.status == ApplicationPhaseStatus.COMPLETED
        )

        if since:
            gen_stmt = gen_stmt.where(Application.created_at >= since)
            util_stmt = util_stmt.where(ApprovedApplicationPhase.completed_at >= since)

        tokens_generated = (await self.session.execute(gen_stmt)).scalar() or 0
        tokens_utilized = (await self.session.execute(util_stmt)).scalar() or 0

        return [
            {
                "label": "Tokens Generated",
                "value": tokens_generated,
                "previous_value": None,
                "percent_change": None,
            },
            {
                "label": "Tokens Utilized",
                "value": tokens_utilized,
                "previous_value": None,
                "percent_change": None,
            },
        ]

    async def nodal_token_status(self, since: Optional[datetime] = None) -> list[dict]:
        """Phase-status breakdown (donut chart)."""
        stmt = select(
            ApprovedApplicationPhase.status,
            func.count(ApprovedApplicationPhase.id).label("count"),
        ).group_by(ApprovedApplicationPhase.status)
        if since:
            stmt = stmt.where(ApprovedApplicationPhase.activated_at >= since)

        rows = (await self.session.execute(stmt)).all()
        return [{"status": r[0].value, "count": r[1]} for r in rows]

    async def nodal_material_approved_vs_used(
        self, since: Optional[datetime] = None
    ) -> list[dict]:
        """Material approved (phase_materials) vs used (naka_entries) bar chart."""
        permitted_sq_stmt = select(
            ApplicationPhaseMaterial.material_id,
            func.coalesce(func.sum(ApplicationPhaseMaterial.quantity), 0).label(
                "approved"
            ),
        ).group_by(ApplicationPhaseMaterial.material_id)

        used_sq_stmt = (
            select(
                VehicleMaterial.material_id,
                func.coalesce(func.sum(VehicleMaterial.quantity), 0).label("used"),
            )
            .join(NakaEntry, VehicleMaterial.vehicle_entry_id == NakaEntry.id)
            .group_by(VehicleMaterial.material_id)
        )

        if since:
            # We don't have a created_at on ApplicationPhaseMaterial directly,
            # but we can join with ApprovedApplicationPhase
            permitted_sq_stmt = permitted_sq_stmt.join(
                ApprovedApplicationPhase,
                and_(
                    ApplicationPhaseMaterial.application_id
                    == ApprovedApplicationPhase.application_id,
                    ApplicationPhaseMaterial.phase == ApprovedApplicationPhase.phase,
                ),
            ).where(ApprovedApplicationPhase.activated_at >= since)

            used_sq_stmt = used_sq_stmt.where(NakaEntry.entry_at >= since)

        permitted_sq = permitted_sq_stmt.subquery()
        used_sq = used_sq_stmt.subquery()

        stmt = (
            select(
                Material.id,
                Material.name,
                Material.unit,
                func.coalesce(permitted_sq.c.approved, 0).label("approved"),
                func.coalesce(used_sq.c.used, 0).label("used"),
            )
            .outerjoin(permitted_sq, Material.id == permitted_sq.c.material_id)
            .outerjoin(used_sq, Material.id == used_sq.c.material_id)
            .where((permitted_sq.c.approved.isnot(None)) | (used_sq.c.used.isnot(None)))
            .order_by(Material.name)
        )
        rows = (await self.session.execute(stmt)).all()
        return [
            {
                "material_id": r[0],
                "material_name": r[1],
                "unit": r[2],
                "approved_quantity": r[3] or 0,
                "used_quantity": r[4] or 0,
            }
            for r in rows
        ]

    async def nodal_token_utilization_list(
        self, limit: int = 20, since: Optional[datetime] = None
    ) -> list[dict]:
        """Token utilization table rows with material summary."""
        # Subquery for consumed quantity per application and phase
        consumed_sq_stmt = (
            select(
                NakaEntry.application_id,
                NakaEntry.phase,
                func.sum(VehicleMaterial.quantity).label("total_used"),
            )
            .join(VehicleMaterial, VehicleMaterial.vehicle_entry_id == NakaEntry.id)
            .group_by(NakaEntry.application_id, NakaEntry.phase)
        )

        # Subquery for approved materials summary per application and phase
        material_summary_sq_stmt = (
            select(
                ApplicationPhaseMaterial.application_id,
                ApplicationPhaseMaterial.phase,
                func.string_agg(Material.name, ", ").label("materials"),
                func.sum(ApplicationPhaseMaterial.quantity).label("total_approved"),
            )
            .join(Material, ApplicationPhaseMaterial.material_id == Material.id)
            .group_by(
                ApplicationPhaseMaterial.application_id, ApplicationPhaseMaterial.phase
            )
        )

        if since:
            consumed_sq_stmt = consumed_sq_stmt.where(NakaEntry.entry_at >= since)
            material_summary_sq_stmt = material_summary_sq_stmt.join(
                ApprovedApplicationPhase,
                and_(
                    ApplicationPhaseMaterial.application_id
                    == ApprovedApplicationPhase.application_id,
                    ApplicationPhaseMaterial.phase == ApprovedApplicationPhase.phase,
                ),
            ).where(ApprovedApplicationPhase.activated_at >= since)

        consumed_sq = consumed_sq_stmt.subquery()
        material_summary_sq = material_summary_sq_stmt.subquery()

        stmt = (
            select(
                Application.id.label("application_id"),
                Application.applicant_name,
                ApprovedApplicationPhase.phase,
                ApprovedApplicationPhase.status.label("phase_status"),
                material_summary_sq.c.materials,
                material_summary_sq.c.total_approved,
                func.coalesce(consumed_sq.c.total_used, 0).label("total_used"),
            )
            .join(
                ApprovedApplicationPhase,
                ApprovedApplicationPhase.application_id == Application.id,
            )
            .outerjoin(
                material_summary_sq,
                and_(
                    material_summary_sq.c.application_id == Application.id,
                    material_summary_sq.c.phase == ApprovedApplicationPhase.phase,
                ),
            )
            .outerjoin(
                consumed_sq,
                and_(
                    consumed_sq.c.application_id == Application.id,
                    consumed_sq.c.phase == ApprovedApplicationPhase.phase,
                ),
            )
            .where(Application.status == ApplicationStatus.TOKEN_GENERATED)
        )

        if since:
            stmt = stmt.where(Application.created_at >= since)

        stmt = stmt.order_by(Application.id.desc(), ApprovedApplicationPhase.phase).limit(limit)

        rows = (await self.session.execute(stmt)).all()
        return [
            {
                "application_id": r[0],
                "applicant_name": r[1],
                "phase": r[2],
                "phase_status": r[3].value if hasattr(r[3], "value") else r[3],
                "material_name": r[4] or "N/A",
                "permitted_quantity": r[5] or 0,
                "used_quantity": r[6] or 0,
            }
            for r in rows
        ]

    async def nodal_vehicle_entry_list(
        self, limit: int = 50, since: Optional[datetime] = None
    ) -> list[dict]:
        """All recent vehicle entries across all nakas (for nodal officer)."""
        # Subquery: total consumed per (application_id, phase, material_id)
        consumed_sq_stmt = (
            select(
                NakaEntry.application_id,
                NakaEntry.phase,
                VehicleMaterial.material_id,
                func.coalesce(func.sum(VehicleMaterial.quantity), 0).label("total_used"),
            )
            .join(VehicleMaterial, VehicleMaterial.vehicle_entry_id == NakaEntry.id)
            .group_by(
                NakaEntry.application_id, NakaEntry.phase, VehicleMaterial.material_id
            )
        )

        if since:
            consumed_sq_stmt = consumed_sq_stmt.where(NakaEntry.entry_at >= since)

        consumed_sq = consumed_sq_stmt.subquery()

        stmt = (
            select(
                ApprovedApplicationPhase.id.label("phase_id"),
                ApprovedApplicationPhase.activated_at,
                NakaEntry.vehicle_number,
                User.name.label("naka_incharge"),
                Material.name.label("material_type"),
                VehicleMaterial.quantity.label("quantity_entered"),
                NakaEntry.entry_at,
                NakaEntry.media,
                func.coalesce(ApplicationPhaseMaterial.quantity, 0).label(
                    "approved_qty"
                ),
                func.coalesce(consumed_sq.c.total_used, 0).label("used_qty"),
            )
            .join(VehicleMaterial, VehicleMaterial.vehicle_entry_id == NakaEntry.id)
            .join(Material, VehicleMaterial.material_id == Material.id)
            .join(User, NakaEntry.entry_by == User.id)
            .join(
                ApprovedApplicationPhase,
                and_(
                    ApprovedApplicationPhase.application_id == NakaEntry.application_id,
                    ApprovedApplicationPhase.phase == NakaEntry.phase,
                ),
            )
            .outerjoin(
                ApplicationPhaseMaterial,
                and_(
                    ApplicationPhaseMaterial.application_id == NakaEntry.application_id,
                    ApplicationPhaseMaterial.phase == NakaEntry.phase,
                    ApplicationPhaseMaterial.material_id == VehicleMaterial.material_id,
                ),
            )
            .outerjoin(
                consumed_sq,
                and_(
                    consumed_sq.c.application_id == NakaEntry.application_id,
                    consumed_sq.c.phase == NakaEntry.phase,
                    consumed_sq.c.material_id == VehicleMaterial.material_id,
                ),
            )
        )

        if since:
            stmt = stmt.where(NakaEntry.entry_at >= since)

        stmt = stmt.order_by(NakaEntry.entry_at.desc()).limit(limit)

        rows = (await self.session.execute(stmt)).all()

        results = []
        for r in rows:
            year = r.activated_at.year if r.activated_at else datetime.now().year
            token_number = f"TKN-{year}-{r.phase_id:03d}"
            remaining = (r.approved_qty or 0) - (r.used_qty or 0)

            media_path = None
            if r.media and isinstance(r.media, dict):
                media_path = r.media.get("path") or r.media.get("url") or str(r.media)
            elif isinstance(r.media, str):
                media_path = r.media

            results.append(
                {
                    "token_number": token_number,
                    "vehicle_number": r.vehicle_number,
                    "naka_incharge": r.naka_incharge,
                    "material_type": r.material_type,
                    "quantity_entered": r.quantity_entered,
                    "entry_at": r.entry_at.isoformat() if r.entry_at else None,
                    "ai_recognition": None,
                    "remaining_quantity": max(remaining, 0),
                    "media_path": media_path,
                }
            )
        return results


# ── Dependency injection ──────────────────────────────────────────────────────


async def get_authority_dashboard_dao(
    session: AsyncSession = Depends(get_db),
) -> AuthorityDashboardDAO:
    return AuthorityDashboardDAO(session)
