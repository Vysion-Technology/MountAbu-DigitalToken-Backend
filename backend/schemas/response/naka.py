"""Response schemas for NAKA checkpoint operations."""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict

from backend.meta import ApplicationPhaseStatus
from backend.schemas.response.master import UserSummary, MaterialResponse


class VehicleMaterialResponse(BaseModel):
    id: int
    material: MaterialResponse
    quantity: float

    model_config = ConfigDict(from_attributes=True)


class VehicleEntryResponse(BaseModel):
    id: int
    phase: int
    vehicle_number: str
    driver_name: Optional[str]
    driver_mobile: Optional[str]
    entry_at: datetime
    entered_by_user: Optional[UserSummary]
    remarks: Optional[str]
    media_path: Optional[str]
    materials: list[VehicleMaterialResponse]

    model_config = ConfigDict(from_attributes=True)


class NakaMaterialSummary(BaseModel):
    """Per-material summary for a phase at the naka checkpoint."""
    material_id: int
    material_name: str
    unit: str
    allowed_qty: int
    brought_qty: int
    remaining_qty: int


class NakaPhaseResponse(BaseModel):
    """Phase-level material summary shown to NAKA incharge. No PII."""
    transport_code: str
    phase: int
    phase_status: ApplicationPhaseStatus
    materials: list[NakaMaterialSummary]
    vehicle_entries: list[VehicleEntryResponse] = []
