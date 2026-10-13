from datetime import date, datetime
from typing import Optional, List
from pydantic import BaseModel, ConfigDict
from backend.meta import VehicleScheduleStatus, ScheduleComplianceStatus


class AvailableSlotItemResponse(BaseModel):
    slot_id: int
    name: str
    start_time: str
    end_time: str
    max_capacity: int
    booked_count: int
    available_capacity: int
    is_available: bool
    is_blackout: bool = False
    blackout_reason: Optional[str] = None
    is_applicable_today: bool = True

    model_config = ConfigDict(from_attributes=True)


class AvailableSlotsResponse(BaseModel):
    date: date
    is_full_day_blackout: bool = False
    blackout_reason: Optional[str] = None
    slots: List[AvailableSlotItemResponse]


class VehicleScheduleResponse(BaseModel):
    id: int
    schedule_code: str
    application_id: int
    token_id: int
    phase: int
    user_id: int
    slot_id: int
    slot_name: Optional[str] = None
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    schedule_date: datetime
    vehicle_number: str
    vehicle_type_id: Optional[int] = None
    vehicle_type_name: Optional[str] = None
    status: VehicleScheduleStatus
    created_at: Optional[datetime] = None
    cancelled_at: Optional[datetime] = None
    transport_code: Optional[str] = None
    property_address: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class TokenScheduleStatusResponse(BaseModel):
    has_active_schedule: bool
    active_schedule: Optional[VehicleScheduleResponse] = None


class CapacityHeatmapSlot(BaseModel):
    slot_id: int
    name: str
    start_time: str
    end_time: str
    max_capacity: int
    booked_count: int
    available_capacity: int
    is_blackout: bool = False
    load_percentage: float


class CapacityHeatmapDay(BaseModel):
    date: date
    day_name: str
    total_capacity: int
    total_booked: int
    total_available: int
    overall_load_percentage: float
    is_full_blackout: bool = False
    blackout_reason: Optional[str] = None
    slots: List[CapacityHeatmapSlot] = []


class CapacityHeatmapResponse(BaseModel):
    start_date: date
    end_date: date
    total_days: int
    days: List[CapacityHeatmapDay]

