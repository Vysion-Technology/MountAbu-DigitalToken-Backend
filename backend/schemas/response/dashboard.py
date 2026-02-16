"""Response schemas for citizen dashboard."""

from typing import List
from pydantic import BaseModel, ConfigDict, Field


# ── Overview cards (matches the 5 top cards in the UI) ────────────────────────

class CitizenOverviewStats(BaseModel):
    """Top-level overview cards shown at the top of the citizen dashboard."""

    total_applications: int = Field(0, description="Citizen's total applications")
    active_applications: int = Field(
        0, description="Applications still pending approval (not rejected/token-generated)"
    )
    tokens_issued: int = Field(
        0, description="Count of phases + renovation tokens issued for citizen's apps"
    )
    total_complaints: int = Field(0, description="Citizen's total complaints")
    closed_complaints: int = Field(0, description="Citizen's resolved/closed complaints")


# ── Material analytics ────────────────────────────────────────────────────────

class MaterialUsageSummary(BaseModel):
    """Permitted vs. used quantities per material for the citizen's applications."""

    material_id: int
    material_name: str
    unit: str
    permitted_quantity: int = Field(0, description="Total permitted across phase-materials")
    used_quantity: int = Field(0, description="Total brought in via naka entries")
    usage_percent: float = Field(0.0, description="used / permitted * 100")


class MaterialAvailableQuantity(BaseModel):
    """Remaining available quantity per material (permitted - used)."""

    material_id: int
    material_name: str
    unit: str
    available_quantity: int = Field(0, description="Remaining permitted quantity")


# ── Phase-wise token usage ───────────────────────────────────────────────────

class PhaseTokenUsage(BaseModel):
    """Count of citizen's phases grouped by phase status."""

    phase_status: str
    count: int


# ── Top-level citizen dashboard response ──────────────────────────────────────

class CitizenDashboardResponse(BaseModel):
    """Full citizen dashboard payload matching the UI design."""

    overview: CitizenOverviewStats
    material_usage: List[MaterialUsageSummary]
    available_quantity: List[MaterialAvailableQuantity]
    phase_token_usage: List[PhaseTokenUsage]

    model_config = ConfigDict(from_attributes=True)
