"""Authority dashboard service – role-aware assembly."""

from datetime import datetime, timedelta
from typing import Optional

from fastapi import Depends

from backend.dao.authority_dashboard import (
    AuthorityDashboardDAO,
    get_authority_dashboard_dao,
)
from backend.meta import UserRole, ApplicationType
from backend.schemas.response.authority_dashboard import (
    AuthorityDashboardResponse,
    AvgVerificationTimeTrend,
    CategoryCount,
    ComplaintRow,
    EntriesByNaka,
    JenApplicationRow,
    KpiCard,
    MaterialBar,
    NakaEntryRow,
    NodalVehicleEntryRow,
    StatusCount,
    TokenUtilizationRow,
    WardActivity,
)
from backend.services.base import BaseService


class AuthorityDashboardService(BaseService):
    """Builds the dashboard payload based on the caller's role."""

    def __init__(self, dao: AuthorityDashboardDAO):
        self.dao = dao

    async def get_dashboard(
        self,
        role: UserRole,
        user_id: int,
        days: int = 7,
        ward_id: Optional[int] = None,
        department_id: Optional[int] = None,
        application_type: Optional[ApplicationType] = None,
    ) -> AuthorityDashboardResponse:
        now = datetime.now()
        since = now - timedelta(days=days)
        prev_end = since
        prev_start = prev_end - timedelta(days=days)

        # Dispatch to role-specific builder
        if role == UserRole.SUPERADMIN:
            return await self._superadmin(since, prev_start, prev_end, ward_id, department_id, application_type=application_type)
        elif role == UserRole.JEN:
            return await self._jen(user_id, since, days, ward_id)
        elif role == UserRole.NAKA_INCHARGE:
            return await self._naka(user_id, since)
        elif role == UserRole.COMMISSIONER:
            return await self._complaint_officer(since, ward_id)
        elif role in (UserRole.AEN, UserRole.RIN, UserRole.SIN):
            return await self._complaint_officer(
                since, ward_id, assigned_to_id=user_id, role=role
            )
        elif role == UserRole.NODAL_OFFICER:
            return await self._superadmin(since, prev_start, prev_end, ward_id, department_id, role=role, application_type=application_type)
        else:
            # DEPT_LAND / DEPT_LEGAL / DEPT_ATP / COLLECTOR → same as superadmin (read-only overview)
            return await self._superadmin(since, prev_start, prev_end, ward_id, department_id, role=role, application_type=application_type)

    # ── builders ──────────────────────────────────────────────────────────

    async def _superadmin(
        self,
        since: datetime,
        prev_start: datetime,
        prev_end: datetime,
        ward_id: Optional[int],
        department_id: Optional[int],
        role: UserRole = UserRole.SUPERADMIN,
        application_type: Optional[ApplicationType] = None,
    ) -> AuthorityDashboardResponse:
        kpis_raw = await self.dao.superadmin_kpis(since, prev_start, prev_end, ward_id, department_id, application_type=application_type)
        status_raw = await self.dao.application_status_breakdown(since, ward_id, department_id, application_type=application_type)
        category_raw = await self.dao.complaints_by_category(since, ward_id, department_id)
        ward_raw = await self.dao.ward_activity(since, department_id, application_type=application_type)

        return AuthorityDashboardResponse(
            role=role.value,
            kpis=[KpiCard(**k) for k in kpis_raw],
            application_status_breakdown=[StatusCount(**s) for s in status_raw],
            complaints_by_category=[CategoryCount(**c) for c in category_raw],
            ward_activity=[WardActivity(**w) for w in ward_raw],
        )

    async def _jen(
        self,
        user_id: int,
        since: datetime,
        days: int,
        ward_id: Optional[int] = None,
    ) -> AuthorityDashboardResponse:
        kpis_raw = await self.dao.jen_kpis(user_id, since, ward_id)
        vstatus = await self.dao.jen_verification_status(user_id, since, ward_id)
        trend = await self.dao.jen_avg_verification_trend(user_id, days)
        latest = await self.dao.jen_latest_applications(user_id, limit=5, ward_id=ward_id)

        # Complaint data for JEN
        complaint_kpis = await self.dao.complaint_officer_kpis(
            since, ward_id, assigned_to_id=user_id
        )
        # Merge complaint KPIs into main KPIs if needed, or just keep them separate?
        # The schema has a single `kpis` list. I'll append them.
        kpis = [KpiCard(**k) for k in kpis_raw]
        kpis.extend([KpiCard(**k) for k in complaint_kpis])

        by_cat = await self.dao.complaints_by_category(
            since, ward_id, assigned_to_id=user_id
        )
        resolution = await self.dao.complaint_resolution_status(
            since, ward_id, assigned_to_id=user_id
        )
        clist = await self.dao.complaint_list(
            limit=20, since=since, ward_id=ward_id, assigned_to_id=user_id
        )

        return AuthorityDashboardResponse(
            role=UserRole.JEN.value,
            kpis=kpis,
            verification_status=[StatusCount(**s) for s in vstatus],
            avg_verification_time_trend=[AvgVerificationTimeTrend(**t) for t in trend],
            latest_applications=[JenApplicationRow(**a) for a in latest],
            complaints_by_category=[CategoryCount(**c) for c in by_cat],
            complaint_resolution_status=[StatusCount(**s) for s in resolution],
            complaint_list=[ComplaintRow(**c) for c in clist],
        )

    async def _naka(self, user_id: int, since: datetime) -> AuthorityDashboardResponse:
        kpis_raw = await self.dao.naka_kpis(user_id, since)
        by_naka = await self.dao.naka_entries_by_user(since)
        entries = await self.dao.naka_vehicle_entry_list(user_id, limit=20, since=since)

        return AuthorityDashboardResponse(
            role=UserRole.NAKA_INCHARGE.value,
            kpis=[KpiCard(**k) for k in kpis_raw],
            entries_by_naka=[EntriesByNaka(**e) for e in by_naka],
            vehicle_entry_list=[NakaEntryRow(**e) for e in entries],
        )

    async def _complaint_officer(
        self,
        since: datetime,
        ward_id: Optional[int] = None,
        assigned_to_id: Optional[int] = None,
        role: UserRole = UserRole.COMMISSIONER,
    ) -> AuthorityDashboardResponse:
        kpis_raw = await self.dao.complaint_officer_kpis(
            since, ward_id, assigned_to_id=assigned_to_id
        )
        by_cat = await self.dao.complaints_by_category(
            since, ward_id, assigned_to_id=assigned_to_id
        )
        resolution = await self.dao.complaint_resolution_status(
            since, ward_id, assigned_to_id=assigned_to_id
        )
        clist = await self.dao.complaint_list(
            limit=20, since=since, ward_id=ward_id, assigned_to_id=assigned_to_id
        )

        return AuthorityDashboardResponse(
            role=role.value,
            kpis=[KpiCard(**k) for k in kpis_raw],
            complaints_by_category=[CategoryCount(**c) for c in by_cat],
            complaint_resolution_status=[StatusCount(**s) for s in resolution],
            complaint_list=[ComplaintRow(**c) for c in clist],
        )

    async def _nodal_officer(self, since: datetime) -> AuthorityDashboardResponse:
        kpis_raw = await self.dao.nodal_kpis(since)
        tstatus = await self.dao.nodal_token_status(since)
        mat = await self.dao.nodal_material_approved_vs_used(since)
        tlist = await self.dao.nodal_token_utilization_list(limit=20, since=since)
        entries = await self.dao.nodal_vehicle_entry_list(limit=50, since=since)

        return AuthorityDashboardResponse(
            role=UserRole.NODAL_OFFICER.value,
            kpis=[KpiCard(**k) for k in kpis_raw],
            token_status=[StatusCount(**s) for s in tstatus],
            material_approved_vs_used=[MaterialBar(**m) for m in mat],
            token_utilization_list=[TokenUtilizationRow(**t) for t in tlist],
            vehicle_entry_list=[NodalVehicleEntryRow(**e) for e in entries],
        )


# ── Dependency injection ──────────────────────────────────────────────────────

async def get_authority_dashboard_service(
    dao: AuthorityDashboardDAO = Depends(get_authority_dashboard_dao),
) -> AuthorityDashboardService:
    return AuthorityDashboardService(dao)
