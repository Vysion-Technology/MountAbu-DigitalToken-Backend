"""Response schemas for authority / role-specific dashboards."""

from typing import List, Optional, Union
from pydantic import BaseModel, ConfigDict, Field


# ═══════════════════════════════════════════════════════════════════════════════
# Shared building blocks
# ═══════════════════════════════════════════════════════════════════════════════

class KpiCard(BaseModel):
    """A single KPI card with optional period-over-period comparison."""

    label: str
    value: int = 0
    previous_value: Optional[int] = None
    percent_change: Optional[float] = Field(
        None, description="Percentage change vs previous period"
    )


class StatusCount(BaseModel):
    """Generic status→count pair."""

    status: str
    count: int


class CategoryCount(BaseModel):
    """Complaint-category→count pair."""

    category_id: Optional[int] = None
    category_name: str
    count: int


class WardActivity(BaseModel):
    """Per-ward aggregated counts (for grouped bar chart)."""

    ward_id: int
    ward_name: str
    applications: int = 0
    approved: int = 0
    tokens_issued: int = 0
    complaints: int = 0


class MaterialBar(BaseModel):
    """Material approved vs used (for bar chart)."""

    material_id: int
    material_name: str
    unit: str
    approved_quantity: int = 0
    used_quantity: int = 0


# ═══════════════════════════════════════════════════════════════════════════════
# JEN-specific
# ═══════════════════════════════════════════════════════════════════════════════

class JenApplicationRow(BaseModel):
    """Compact application record for JEN's latest-applications table."""

    application_id: int
    applicant_name: str
    application_type: str
    status: str
    inspected: bool = False


class AvgVerificationTimeTrend(BaseModel):
    """Average verification turnaround bucket (for line chart)."""

    period: str  # e.g. "2026-02-10"
    avg_hours: float = 0.0


# ═══════════════════════════════════════════════════════════════════════════════
# Naka Incharge–specific
# ═══════════════════════════════════════════════════════════════════════════════

class NakaEntryRow(BaseModel):
    """Vehicle entry row for Naka Incharge table."""

    naka_entry_id: int
    application_id: int
    vehicle_number: Optional[str] = None
    material_name: str
    quantity_brought: int
    entry_at: Optional[str] = None


class EntriesByNaka(BaseModel):
    """Entries count per naka user (for bar chart)."""

    user_id: int
    user_name: str
    entry_count: int


# ═══════════════════════════════════════════════════════════════════════════════
# Complaint Officer–specific
# ═══════════════════════════════════════════════════════════════════════════════

class ComplaintRow(BaseModel):
    """Compact complaint record for complaint list table."""

    complaint_id: int
    title: str
    category_name: Optional[str] = None
    status: str
    applicant_name: str
    created_at: Optional[str] = None


# ═══════════════════════════════════════════════════════════════════════════════
# Nodal Officer–specific
# ═══════════════════════════════════════════════════════════════════════════════

class TokenUtilizationRow(BaseModel):
    """Token utilization row for Nodal Officer table."""

    application_id: int
    applicant_name: str
    phase: int
    phase_status: str
    material_name: Optional[str] = None
    permitted_quantity: int = 0
    used_quantity: int = 0


class NodalVehicleEntryRow(BaseModel):
    """Vehicle entry row for Nodal Officer dashboard."""

    token_number: str
    vehicle_number: Optional[str] = None
    naka_incharge: Optional[str] = None
    material_type: Optional[str] = None
    quantity_entered: float = 0
    entry_at: Optional[str] = None
    ai_recognition: Optional[str] = None  # Not in DB, always None for now
    remaining_quantity: float = 0
    media_path: Optional[str] = None


# ═══════════════════════════════════════════════════════════════════════════════
# Top-level authority dashboard response
# ═══════════════════════════════════════════════════════════════════════════════

class AuthorityDashboardResponse(BaseModel):
    """
    Combined authority dashboard payload.

    Sections are **Optional** — only the ones relevant to the caller's role
    are populated; the rest stay ``None``.
    """

    role: str = Field(..., description="Role of the requesting user")

    # ── Shared KPIs ──────────────────────────────────────────────────────
    kpis: List[KpiCard] = []

    # ── Super Admin ──────────────────────────────────────────────────────
    application_status_breakdown: Optional[List[StatusCount]] = None
    complaints_by_category: Optional[List[CategoryCount]] = None
    ward_activity: Optional[List[WardActivity]] = None

    # ── JEN ───────────────────────────────────────────────────────────────
    verification_status: Optional[List[StatusCount]] = None
    avg_verification_time_trend: Optional[List[AvgVerificationTimeTrend]] = None
    latest_applications: Optional[List[JenApplicationRow]] = None

    # ── Naka Incharge ─────────────────────────────────────────────────────
    entries_by_naka: Optional[List[EntriesByNaka]] = None
    vehicle_entry_list: Optional[List[Union[NodalVehicleEntryRow, NakaEntryRow]]] = None

    # ── Complaint Officer (Commissioner) ──────────────────────────────────
    complaint_resolution_status: Optional[List[StatusCount]] = None
    complaint_list: Optional[List[ComplaintRow]] = None

    # ── Nodal Officer ─────────────────────────────────────────────────────
    token_status: Optional[List[StatusCount]] = None
    material_approved_vs_used: Optional[List[MaterialBar]] = None
    token_utilization_list: Optional[List[TokenUtilizationRow]] = None

    model_config = ConfigDict(from_attributes=True)
