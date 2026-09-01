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
    material_id: Optional[int] = None
    custom_name: Optional[str] = None
    material_name: str
    unit: str
    allowed_qty: float
    brought_qty: float
    remaining_qty: float


class NakaScheduleInfo(BaseModel):
    """Vehicle scheduling details shown to Naka incharge upon token scan."""
    schedule_id: int
    schedule_code: str
    schedule_date: str
    slot_name: str
    start_time: str
    end_time: str
    vehicle_number: str
    vehicle_type: Optional[str] = None
    is_today: bool
    status: str


class NakaPhaseResponse(BaseModel):
    """Phase-level material summary shown to NAKA incharge. No PII."""
    transport_code: str
    phase: int
    phase_status: ApplicationPhaseStatus
    materials: list[NakaMaterialSummary]
    vehicle_entries: list[VehicleEntryResponse] = []
    schedule_info: Optional[NakaScheduleInfo] = None

